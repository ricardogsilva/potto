import asyncio
import json
import logging
from typing import Literal

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

from . import (
    config,
    constants,
)
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
    _pygeoapi_api: _API

    def __init__(self, pygeoapi_api: _API) -> None:
        self._pygeoapi_api = pygeoapi_api

    @classmethod
    def from_settings(cls, settings: config.PottoSettings):
        pygeoapi_config = config.get_pygeoapi_config(settings)
        openapi_document = get_oas_30(pygeoapi_config, fail_on_invalid_collection=True)
        core_api = _API(config=pygeoapi_config, openapi=openapi_document)
        return cls(core_api)

    def get_raw_config(self) -> dict:
        return self._pygeoapi_api.config.copy()

    def list_resource_configs(self) -> dict:
        return self.get_raw_config().get("resources", {})

    def _list_raw_item_collection_resource_configs(self) -> dict[str, dict]:
        return {
            id_: resource.copy()
            for id_, resource in self.list_resource_configs().items()
            if resource.get("type", "collection") == "collection"
        }

    def _get_raw_item_collection_config(self, collection_id: str) -> dict:
        return self._list_raw_item_collection_resource_configs().get(collection_id)

    def list_item_collection_configs(self) -> list[ItemCollectionConfig]:
        return [
            ItemCollectionConfig.from_pygeoapi_config(id_, raw_conf)
            for id_, raw_conf
            in self._list_raw_item_collection_resource_configs().items()
        ]

    def get_item_collection_config(self, collection_id: str) -> ItemCollectionConfig:
        return ItemCollectionConfig.from_pygeoapi_config(
            collection_id,
            self._get_raw_item_collection_config(collection_id)
        )

    def _list_raw_stac_collection_resource_configs(self) -> dict:
        return {
            id_: resource.copy()
            for id_, resource in self.list_resource_configs().items()
            if resource.get("type", "stac-collection")
        }

    def _list_raw_process_resource_configs(self) -> dict:
        return {
            id_: resource.copy()
            for id_, resource in self.list_resource_configs().items()
            if resource.get("type", "process")
        }

    def get_server_identification_config(self) -> ServerMetadataIdentificationConfig:
        return ServerMetadataIdentificationConfig.from_pygeoapi_config(
            self.get_raw_config()["metadata"]["identification"])

    def get_localized_config(self, locale: babel.Locale) -> dict:
        return translate_struct(
            self.get_raw_config(),
            locale_=locale,
            is_config=True
        )

    def has_item_collection_resources(self) -> bool:
        return len(self.list_item_collection_configs()) > 0

    def has_stac_collection_resources(self) -> bool:
        return len(self._list_raw_stac_collection_resource_configs()) > 0

    def has_process_resources(self) -> bool:
        return len(self._list_raw_process_resource_configs()) > 0

    def has_tiles(self) -> bool:
        for resource in self._list_raw_item_collection_resource_configs().values():
            for provider in resource.get("providers", []):
                if provider.get("type") == "tile":
                    return True
        return False

    async def api_get_landing_page(
            self, *, language: str | None = None) -> potto_schemas.LandingPage:
        identification_config = self.get_server_identification_config()
        return potto_schemas.LandingPage(
            title=identification_config.title.get_value(language),
            description=identification_config.description.get_value(language),
            attribution=None,
            collections=[
                collections_schemas.Collection.from_config(coll_conf, language)
                for coll_conf in self.list_item_collection_configs()
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
        return potto_schemas.PottoResponse(
            content_type=_FORMAT_TYPES[F_JSON],
            content=self._pygeoapi_api.openapi
        )

    async def api_list_collections(
            self,
            *,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> potto_schemas.CollectionList:
        pygeoapi_response = _describe_collections(
            self._pygeoapi_api,
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
        pygeoapi_response = _describe_collections(
            self._pygeoapi_api,
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
            resource=self.get_item_collection_config(collection_id),
            metadata={**pygeoapi_headers}
        )

    async def api_list_collection_items(
            self,
            *,
            collection_id: str,
            locale: babel.Locale,
            filter_: collections_schemas.FeatureFilter | None = None,
    ) -> potto_schemas.CollectionFeatureListResponse:
        pygeoapi_response = await asyncio.to_thread(
            _get_collection_items,
            self._pygeoapi_api,
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
        collection_config = self.get_item_collection_config(collection_id)
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
                    requested=filter_.limit,
                    server_limits=self._pygeoapi_api.config["server"].get("limits", {}),
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
        pygeoapi_response = await asyncio.to_thread(
            _get_collection_item,
            self._pygeoapi_api,
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
        collection_config = self.get_item_collection_config(collection_id)
        return potto_schemas.FeatureResponse(
            resource=collection_config,
            provider=collection_config.get_default_provider_config(type_="feature"),
            feature=collections_schemas.Feature.from_original_feature(parsed_pygeoapi_content),
            metadata=pygeoapi_headers
        )
