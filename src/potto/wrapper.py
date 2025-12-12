import asyncio
import json
import logging
from typing import Literal

import babel
from pygeoapi.api import (
    API as _API,
    landing_page as _landing_page,
    conformance as _conformance,
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

from . import config
from .schemas import items
from .schemas.pygeoapi_config import ItemCollectionConfig
from .schemas.potto import (
    PottoResponse,
    CollectionFeatureListResponse,
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

    def list_item_collection_resource_configs(self) -> dict:
        return {
            id_: resource.copy()
            for id_, resource in self.list_resource_configs().items()
            if resource.get("type", "collection")
        }

    def get_item_collection_config(self, collection_id: str) -> ItemCollectionConfig:
        return ItemCollectionConfig.from_pygeoapi_config(
            collection_id,
            self.get_raw_item_collection_config(collection_id)
        )

    def get_raw_item_collection_config(self, collection_id: str) -> dict:
        return self.list_item_collection_resource_configs().get(collection_id)

    def list_stac_collection_resource_configs(self) -> dict:
        return {
            id_: resource.copy()
            for id_, resource in self.list_resource_configs().items()
            if resource.get("type", "stac-collection")
        }

    def list_process_resource_configs(self) -> dict:
        return {
            id_: resource.copy()
            for id_, resource in self.list_resource_configs().items()
            if resource.get("type", "process")
        }

    def get_localized_config(self, locale: babel.Locale) -> dict:
        return translate_struct(
            self.get_raw_config(),
            locale_=locale,
            is_config=True
        )

    def has_item_collection_resources(self) -> bool:
        return len(self.list_item_collection_resource_configs()) > 0

    def has_stac_collection_resources(self) -> bool:
        return len(self.list_stac_collection_resource_configs()) > 0

    def has_process_resources(self) -> bool:
        return len(self.list_process_resource_configs()) > 0

    def has_tiles(self) -> bool:
        for resource in self.list_item_collection_resource_configs().values():
            for provider in resource.get("providers", []):
                if provider.get("type") == "tile":
                    return True
        return False

    async def api_get_landing_page(
            self,
            *,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> PottoResponse:
        original_response = _landing_page(
            self._pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format=output_format,
            )

        )
        original_headers, original_status_code, original_content = original_response
        return PottoResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )

    async def api_get_conformance_details(
            self,
            *,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> PottoResponse:
        original_response = _conformance(
            self._pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format=output_format,
            )
        )
        original_headers, original_status_code, original_content = original_response
        return PottoResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )

    async def api_get_openapi_document(
            self,
    ) -> PottoResponse:
        return PottoResponse(
            content_type=_FORMAT_TYPES[F_JSON],
            content=self._pygeoapi_api.openapi
        )

    async def api_list_collections(
            self,
            *,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> PottoResponse:
        original_response = _describe_collections(
            self._pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format=output_format,
            ),
            dataset=None
        )
        original_headers, original_status_code, original_content = original_response
        return PottoResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )

    async def api_get_collection(
            self,
            *,
            collection_id: str,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> PottoResponse:
        original_response = _describe_collections(
            self._pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format=output_format,
            ),
            dataset=collection_id
        )
        original_headers, original_status_code, original_content = original_response
        return PottoResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )

    async def api_list_collection_items(
            self,
            *,
            collection_id: str,
            locale: babel.Locale,
            filter_: items.FeatureCollectionFilter | None = None,
    ) -> CollectionFeatureListResponse:
        pygeoapi_response = await asyncio.to_thread(
            _get_collection_items,
            self._pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format="json",
                **filter_.as_kwargs()
            ),
            dataset=collection_id
        )
        pygeoapi_headers, pygeoapi_status_code, pygeoapi_content = pygeoapi_response
        parsed_pygeoapi_content = json.loads(pygeoapi_content)
        logger.debug(f"{parsed_pygeoapi_content=}")
        collection_config = self.get_item_collection_config(collection_id)
        features=[
            items.Feature.from_original_feature(feat)
            for feat in parsed_pygeoapi_content["features"]
        ]
        return CollectionFeatureListResponse(
            resource=collection_config,
            provider=collection_config.get_default_provider_config(type_="feature"),
            features=features,
            pagination=items.FeatureCollectionPaginationContext(
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
    ) -> PottoResponse:
        original_response = _get_collection_item(
            self._pygeoapi_api,
            PottoRequest(
                locale=locale,
                output_format=output_format,
            ),
            dataset=collection_id,
            identifier=item_id,
        )
        original_headers, original_status_code, original_content = original_response
        return PottoResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )
