import asyncio
import copy
import json
import logging
import os
import re
from typing import (
    Literal,
    Sequence,
    TypeAlias,
)

import babel
import shapely
from pygeoapi.api import (
    API as _API,
    describe_collections as _describe_collections,
    evaluate_limit as _evaluate_limit,
    F_JSON,
    FORMAT_TYPES as _FORMAT_TYPES,
)
from pygeoapi.api.itemtypes import (
    get_collection_items as _get_collection_items,
    get_collection_item as _get_collection_item,
)
from pygeoapi.openapi import get_oas_30
from pygeoapi.l10n import translate_struct
from pygeoapi.util import yaml_load

from . import constants
from .config import PottoSettings
from .db.models import CollectionResource
from .db.queries.collections import collect_all_collections
from .schemas import (
    collections as collections_schemas,
    potto as potto_schemas,
)
from .schemas.pygeoapi_config import (
    ItemCollectionConfig,
    ServerMetadataIdentificationConfig,
)
from .webapp.requests import PottoRequest

logger = logging.getLogger(__name__)

ResourceTypes: TypeAlias = Sequence[Literal["collection", "stac-collection", "process"]]


async def get_pygeoapi_config(
        settings: PottoSettings,
        *,
        resource_types: ResourceTypes | Literal["all"] = "all",
        resource_page: int = 1,
        resource_page_size: int | None = None,
) -> dict:
    read_conf = yaml_load(settings.pygeoapi_config_file.read_text())
    server_conf = read_conf.get("server", {})
    server_map = server_conf.get("map", {})
    server_limits_conf = server_conf.get("limits", {})
    metadata_conf = read_conf.get("metadata", {})
    identification_conf = metadata_conf.get("identification", {})
    license_conf = metadata_conf.get("license", {})
    provider_conf = metadata_conf.get("provider", {})
    contact_conf = metadata_conf.get("contact", {})
    pygeoapi_config = {
        "server": {
            "admin": server_conf.get("admin", False),
            "languages": settings.locales,
            "limits": {
                "default_items": server_limits_conf.get("default_items", 20),
                "max_items": server_limits_conf.get("max_items", 50),
            },
            "map": {
                "url": server_map.get(
                    "map", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
                "attribution": server_map.get(
                    "attribution",
                    '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap contributors</a>'
                ),
            },
            "locale_dir": server_conf.get("locale_dir"),
            "url": settings.public_url,
        },
        "logging": {
            "level": "DEBUG" if settings.debug else "WARNING"
        },
        "metadata": {
            "identification": {
                "title": identification_conf.get(
                    "title", {"en": "Potto"}
                ),
                "description": identification_conf.get(
                    "description", {"en": "The pygeoapi primate"}
                ),
                "keywords": identification_conf.get(
                    "keywords", {"en": ["geospatial", "data", "api"]}
                ),
                "keywords_type": identification_conf.get("keywords_type", "theme"),
                "terms_of_service": identification_conf.get(
                    "terms_of_service", "https://creativecommons.org/licenses/by/4.0/"),
                "url": identification_conf.get("url", "https://example.org"),
            },
            "license": {
                "name": license_conf.get("name", "CC-BY 4.0 license"),
                "url": license_conf.get("url", "https://creativecommons.org/licenses/by/4.0/"),
            },
            "provider": {
                "name": provider_conf.get("name", "Organization Name"),
                "url": provider_conf.get("url", "https://pygeoapi.io"),
            },
            "contact": {
                "name": contact_conf.get("name", "Lastname, Firstname"),
                "position": contact_conf.get("position", "Position Title"),
                "address": contact_conf.get("address", "Mailing Address"),
                "city": contact_conf.get("city", "City"),
                "stateorprovince": contact_conf.get("stateorprovince", "Administrative Area"),
                "postalcode": contact_conf.get("postalcode", "Zip or Postal Code"),
                "country": contact_conf.get("country", "Country"),
                "phone": contact_conf.get("phone", "+xx-xxx-xxx-xxxx"),
                "fax": contact_conf.get("fax", "+xx-xxx-xxx-xxxx"),
                "email": contact_conf.get("email", "you@example.org"),
                "url": contact_conf.get("url", "Contact URL"),
                "hours": contact_conf.get("hours", "Mo-Fr 08:00-17:00"),
                "instructions": contact_conf.get("instructions", "During hours of service. Off on weekends."),
                "role": contact_conf.get("role", "pointOfContact"),
            },
        },
        "resources": read_conf.get("resources", {}),
    }

    session_maker = settings.get_db_session_maker()
    async with session_maker() as db_session:
        all_collections = await collect_all_collections(db_session)
        for db_collection in all_collections:
            pygeoapi_config["resources"][db_collection.resource_identifier] = (
                _convert_collection_to_pygeoapi_resource(db_collection)
            )

    # filter and paginate the resources - in a future iteration, when we stop
    # reading the config both from a file and from the db (and just read it all
    # from the db), we can perform these on the db side, which will be more
    # efficient
    resource_filter = (
        ("collection", "stac-collection", "process")
        if resource_types == "all" else resource_types
    )
    resources_as_list = [
        (id_, res)
        for id_, res in pygeoapi_config["resources"].items()
        if res.get("type") in resource_filter
    ]
    if resource_page_size is None:
        relevant_resources = resources_as_list
    else:
        offset = (max(resource_page - 1, 0)) * resource_page_size
        relevant_indexes = slice(
            offset,
            min(offset + resource_page_size, len(resources_as_list))
        )
        relevant_resources = resources_as_list[relevant_indexes]
    pygeoapi_config["resources"] = {id_: res for id_, res in relevant_resources}
    # TODO: validate the config
    return pygeoapi_config


def _convert_collection_to_pygeoapi_resource(
        collection: CollectionResource) -> dict:
    links = []
    for collection_link in collection.additional_links or []:
        link_ = dict(collection_link)
        type_ = link_.pop("media_type", "")
        links.append(
            {
                "type": type_,
                **link_
            }
        )
    providers = []
    for provider in collection.providers or []:
        raw_data_value = provider.pop("data", "")
        interpolated_data_value = re.sub(
            r"\${?(\w+)}?",
            lambda re_match: os.getenv(re_match.group(1), "ENV_VAR_NOT_FOUND"),
            raw_data_value,
        )
        provider["data"] = interpolated_data_value
        providers.append(provider)

    return {
        "type": "collection",
        "title": collection.title,
        "description": collection.description or "",
        "keywords": collection.keywords or [],
        "linked-data": None,
        "links": links,
        "extents": {
            "spatial": {
                "bbox": (
                    collection.spatial_extent.bounds
                    if collection.spatial_extent
                    else shapely.box(-180, -90, 180, 90).bounds
                ),
                "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84",
            },
            "temporal": {
                "begin": (
                    collection.temporal_extent_begin.isoformat()
                    if collection.temporal_extent_begin else None
                ),
                "end": (
                    collection.temporal_extent_end.isoformat()
                    if collection.temporal_extent_end else None
                ),
            }
        },
        "providers": providers,
    }


class Potto:
    """A wrapper around pygeoapi core.

    This wrapper presents a simpler interface than pygeoapi core and also
    implements some additional operations.

    The major difference from pygeoapi core is that this wrapper's methods
    accept direct arguments rather than receiving a generic `Request` class
    and then parsing the contents of the request. This means that this class
    demands that parsing of an HTTP request be done before calling it, or in
    other words, that the framework that is wrapping pygeoapi core deals with
    the complexity of retrieving parameters from the HTTP request.

    Note that internally this class' methods still need to construct a
    `Request` instance in order to send to pygeoapi core, which expects it.
    But the interface they present to the world is request-free. This is done
    with two intentions:

    - Allow non HTTP clients to use pygeoapi core. For example, a CLI
      application
    - Demonstrate what pygeoapi core's public API would look like if it did
      not focus on parsing HTTP Requests but rather whatever input parameters
      were needed for each particular method
    """
    _settings: PottoSettings

    def __init__(self, settings: PottoSettings) -> None:
        self._settings = settings

    async def _get_core_api(
            self,
            resource_types: ResourceTypes | Literal["all"] = "all",
            resource_page: int = 1,
            resource_page_size: int | None = None,
    ) -> _API:
        pygeoapi_config = await get_pygeoapi_config(
            self._settings,
            resource_types=resource_types,
            resource_page=resource_page,
            resource_page_size=resource_page_size
        )
        openapi_document = get_oas_30(pygeoapi_config, fail_on_invalid_collection=True)
        return _API(config=pygeoapi_config, openapi=openapi_document)

    async def list_resource_configs(
            self,
            resource_types: ResourceTypes | Literal["all"] = "all",
            page: int = 1,
            page_size: int | None = 20,
    ) -> list[ItemCollectionConfig | tuple[str, dict]]:
        pygeoapi_api = await self._get_core_api(
            resource_types=resource_types,
            resource_page=page,
            resource_page_size=page_size,
        )
        result = []
        for id_, raw_resource in pygeoapi_api.config["resources"].items():
            if (type_ := raw_resource.get("type")) == "collection":
                result.append(
                    ItemCollectionConfig.from_pygeoapi_config(id_, raw_resource))
            elif type_ in ("stac-collection", "process"):
                result.append((id_, raw_resource))
            else:
                logger.warning(
                    f"Resource {id_} has unknown resource type {type_!r}, ignoring...")
        return result

    async def list_process_configs(
            self, page: int = 1, page_size: int | None = 20
    ) -> list[tuple[str, dict]]:
        pygeoapi_api = await self._get_core_api(
            resource_types=["process"],
            resource_page=page,
            resource_page_size=page_size,
        )
        return list(pygeoapi_api.config["resources"].items())

    async def list_item_collection_configs(
            self, page: int = 1, page_size: int | None = 20
    ) -> list[ItemCollectionConfig]:
        pygeoapi_api = await self._get_core_api(
            resource_types=["collection"],
            resource_page=page,
            resource_page_size=page_size,
        )
        return [
            ItemCollectionConfig.from_pygeoapi_config(id_, raw_conf)
            for id_, raw_conf in pygeoapi_api.config["resources"].items()
        ]

    async def list_stac_collection_configs(
            self, page: int = 1, page_size: int | None = 20
    ) -> list[tuple[str, dict]]:
        pygeoapi_api = await self._get_core_api(
            resource_types=["stac-collection"],
            resource_page=page,
            resource_page_size=page_size,
        )
        return list(pygeoapi_api.config["resources"].items())

    async def get_item_collection_config(
            self, collection_id: str) -> ItemCollectionConfig | None:
        # TODO: in a future iteration, when we are no longer reading the
        #  config from both a file and the db (and read it all from the db),
        #  we can skip instantiation of pygeoapi api and just retrieve the
        #  item directly
        pygeoapi_api = await self._get_core_api()
        if not (
                raw_resource := pygeoapi_api.config.get(
                    "resources", {}).get(collection_id)
        ):
            return None

        if not raw_resource.get("type") == "collection":
            logger.warning(f"resource {collection_id!r} is not of type 'collection'")
            return None

        return ItemCollectionConfig.from_pygeoapi_config(collection_id, raw_resource)

    async def get_server_identification_config(self) -> ServerMetadataIdentificationConfig:
        pygeoapi_api = await self._get_core_api(resource_page_size=0)
        return ServerMetadataIdentificationConfig.from_pygeoapi_config(
            pygeoapi_api.config["metadata"]["identification"])

    async def get_localized_config(self, locale: babel.Locale) -> dict:
        pygeoapi_api = await self._get_core_api()
        return translate_struct(
            pygeoapi_api.config,
            locale_=locale,
            is_config=True
        )

    async def api_get_landing_page(
            self, *, language: str | None = None) -> potto_schemas.LandingPage:
        identification_config = await self.get_server_identification_config()
        return potto_schemas.LandingPage(
            title=identification_config.title.get_value(language),
            description=identification_config.description.get_value(language),
            attribution=None,
            # TODO: add processes and stac collections too
            collections=[
                collections_schemas.Collection.from_config(coll_conf, language)
                for coll_conf in await self.list_item_collection_configs(page_size=20)
            ]
        )

    async def api_get_conformance_details(self) -> potto_schemas.ConformanceDetail:
        return potto_schemas.ConformanceDetail(
            conforms_to=[
                constants.CONFORMANCE_CLASS_OGCAPI_FEATURES_CORE,
                constants.CONFORMANCE_CLASS_OGCAPI_FEATURES_GEOJSON,
                constants.CONFORMANCE_CLASS_OGCAPI_FEATURES_OPENAPI3
            ]
        )

    async def api_get_openapi_document(
            self,
    ) -> potto_schemas.PottoResponse:
        pygeoapi_api = await self._get_core_api()
        return potto_schemas.PottoResponse(
            content_type=_FORMAT_TYPES[F_JSON],
            content=pygeoapi_api.openapi
        )

    async def api_list_collections(
            self,
            *,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> potto_schemas.CollectionList:
        # TODO: this ought to be paginated
        pygeoapi_api = await self._get_core_api(
            resource_types=["collection"],
            resource_page_size=None
        )
        pygeoapi_response = _describe_collections(
            pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format=output_format,
            ),
            dataset=None
        )
        pygeoapi_headers, pygeoapi_status_code, pygeoapi_content = pygeoapi_response
        parsed_pygeoapi_content = json.loads(pygeoapi_content)
        return potto_schemas.CollectionList(
            collections=[
                collections_schemas.Collection(**i)
                for i in parsed_pygeoapi_content["collections"]
            ],
            pagination=None,
            filter_=None,
            metadata={**pygeoapi_headers}
        )

    async def api_get_collection(
            self,
            *,
            collection_id: str,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> potto_schemas.CollectionDetail:
        pygeoapi_api = await self._get_core_api(
            resource_types=["collection"],
            resource_page_size=None
        )
        pygeoapi_response = _describe_collections(
            pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format=output_format,
            ),
            dataset=collection_id
        )
        pygeoapi_headers, pygeoapi_status_code, pygeoapi_content = pygeoapi_response
        parsed_pygeoapi_content = json.loads(pygeoapi_content)
        return potto_schemas.CollectionDetail(
            collection=collections_schemas.Collection(**parsed_pygeoapi_content),
            resource=await self.get_item_collection_config(collection_id),
            metadata={**pygeoapi_headers}
        )

    async def api_list_collection_items(
            self,
            collection_id: str,
            *,
            locale: babel.Locale,
            filter_: collections_schemas.FeatureFilter | None = None,
    ) -> potto_schemas.CollectionFeatureListResponse:
        pygeoapi_api = await self._get_core_api(
            resource_types=["collection"],
            resource_page_size=None
        )
        pygeoapi_response = await asyncio.to_thread(
            _get_collection_items,
            pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format="json",
                **(filter_.model_dump(by_alias=True, exclude_none=True) if filter_ else {})
            ),
            dataset=collection_id
        )
        pygeoapi_headers, pygeoapi_status_code, pygeoapi_content = pygeoapi_response
        parsed_pygeoapi_content = json.loads(pygeoapi_content)
        logger.debug(f"{parsed_pygeoapi_content=}")
        collection_config = await self.get_item_collection_config(collection_id)
        features=[
            collections_schemas.Feature.from_original_feature(feat)
            for feat in parsed_pygeoapi_content["features"]
        ]
        return potto_schemas.CollectionFeatureListResponse(
            resource=collection_config,
            provider=collection_config.get_default_provider_config(type_="feature"),
            features=features,
            pagination=collections_schemas.CollectionItemsPaginationContext(
                limit=_evaluate_limit(
                    requested=filter_.limit if filter_ else None,
                    server_limits=pygeoapi_api.config["server"].get("limits", {}),
                    collection_limits=(
                        col_limits.as_pygeoapi_config
                        if (col_limits := collection_config.limits) else {}
                    ),
                ),
                number_matched=parsed_pygeoapi_content.get("numberMatched", 0),
                number_returned=parsed_pygeoapi_content.get("numberReturned", len(features)),
                offset=parsed_pygeoapi_content.get("offset", 0),
            ),
            filter_=filter_,
            metadata={
                **pygeoapi_headers,
                "timestamp": parsed_pygeoapi_content.get("timeStamp"),
            },
        )

    async def api_get_item(
            self,
            *,
            item_id: str,
            collection_id: str,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> potto_schemas.FeatureResponse:
        pygeoapi_api = await self._get_core_api(
            resource_types=["collection"], resource_page_size=None)
        pygeoapi_response = await asyncio.to_thread(
            _get_collection_item,
            pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format=output_format,
            ),
            dataset=collection_id,
            identifier=item_id,
        )
        pygeoapi_headers, pygeoapi_status_code, pygeoapi_content = pygeoapi_response
        logger.debug(f"{pygeoapi_content=}")
        logger.debug(f"{pygeoapi_headers=}")
        logger.debug(f"{pygeoapi_status_code=}")

        parsed_pygeoapi_content = json.loads(pygeoapi_content)
        collection_config = await self.get_item_collection_config(collection_id)
        return potto_schemas.FeatureResponse(
            resource=collection_config,
            provider=collection_config.get_default_provider_config(type_="feature"),
            feature=collections_schemas.Feature.from_original_feature(parsed_pygeoapi_content),
            metadata=pygeoapi_headers
        )
