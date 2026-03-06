import asyncio
import json
import logging
from typing import (
    Literal,
    Sequence,
    TypeAlias,
)

import babel
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

from . import constants
from .config import PottoSettings
from .db.queries.metadata import get_metadata
from .db.queries.collections import paginated_list_collections
from .operations.config import get_pygeoapi_config
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
        async with self._settings.get_db_session_maker()() as session:
            pygeoapi_config = await get_pygeoapi_config(
                session,
                self._settings.locales,
                self._settings.public_url,
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

    async def list_collections(
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

    async def get_localized_config(self, locale: babel.Locale) -> dict:
        pygeoapi_api = await self._get_core_api()
        return translate_struct(
            pygeoapi_api.config,
            locale_=locale,
            is_config=True
        )

    async def api_get_landing_page(
            self, *, language: str | None = None) -> potto_schemas.LandingPage:
        """Return overview information.

        The response contains useful info for generating a landing page for the API.

        Note: This method bypasses pygeoapi.
        """
        async with self._settings.get_db_session_maker()() as session:
            db_metadata = await get_metadata(session)
            db_collections, total = await paginated_list_collections(session, include_total=True)
        return potto_schemas.LandingPage(
            metadata=db_metadata,
            attribution=None,
            # TODO: add processes and stac collections too
            collections=db_collections,
            num_collections=total,
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
