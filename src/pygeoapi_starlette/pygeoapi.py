import dataclasses
import json
from typing import Literal

import babel
from pygeoapi.api import (
    API as _API,
    landing_page as _landing_page,
    conformance as _conformance,
    describe_collections as _describe_collections,
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
from .webapp.requests import PygeoapiStarletteRequest


@dataclasses.dataclass(frozen=True)
class PygeoapiResponse:
    content_type: str
    content: dict | bytes
    metadata: dict [str, str] | None = None


class PygeoapiStarlette:
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
    def from_settings(cls, settings: config.PygeoapiStarletteSettings):
        pygeoapi_config = config.get_pygeoapi_config(settings)
        openapi_document = get_oas_30(pygeoapi_config, fail_on_invalid_collection=True)
        core_api = _API(config=pygeoapi_config, openapi=openapi_document)
        return cls(core_api)

    def get_raw_config(self) -> dict:
        return self._pygeoapi_api.config.copy()

    def get_resources(self) -> dict:
        return self.get_raw_config().get("resources", {})

    def get_item_collection_resources(self) -> dict:
        return {
            id_: resource.copy()
            for id_, resource in self.get_resources().items()
            if resource.get("type", "collection")
        }

    def get_stac_collection_resources(self) -> dict:
        return {
            id_: resource.copy()
            for id_, resource in self.get_resources().items()
            if resource.get("type", "stac-collection")
        }

    def get_process_resources(self) -> dict:
        return {
            id_: resource.copy()
            for id_, resource in self.get_resources().items()
            if resource.get("type", "process")
        }

    def get_localized_config(self, locale: babel.Locale) -> dict:
        return translate_struct(
            self.get_raw_config(),
            locale_=locale,
            is_config=True
        )

    def has_item_collection_resources(self) -> bool:
        return len(self.get_item_collection_resources()) > 0

    def has_stac_collection_resources(self) -> bool:
        return len(self.get_stac_collection_resources()) > 0

    def has_process_resources(self) -> bool:
        return len(self.get_process_resources()) > 0

    def has_tiles(self) -> bool:
        for resource in self.get_item_collection_resources().values():
            for provider in resource.get("providers", []):
                if provider.get("type") == "tile":
                    return True
        return False

    async def get_landing_page(
            self,
            *,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> PygeoapiResponse:
        original_response = _landing_page(
            self._pygeoapi_api,
            PygeoapiStarletteRequest(
                locale=locale,
                output_format=output_format,
            )

        )
        original_headers, original_status_code, original_content = original_response
        return PygeoapiResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )

    async def get_conformance_details(
            self,
            *,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> PygeoapiResponse:
        original_response = _conformance(
            self._pygeoapi_api,
            PygeoapiStarletteRequest(
                locale=locale,
                output_format=output_format,
            )
        )
        original_headers, original_status_code, original_content = original_response
        return PygeoapiResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )

    async def get_openapi_document(
            self,
    ) -> PygeoapiResponse:
        return PygeoapiResponse(
            content_type=_FORMAT_TYPES[F_JSON],
            content=self._pygeoapi_api.openapi
        )

    async def list_collections(
            self,
            *,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> PygeoapiResponse:
        original_response = _describe_collections(
            self._pygeoapi_api,
            PygeoapiStarletteRequest(
                locale=locale,
                output_format=output_format,
            ),
            dataset=None
        )
        original_headers, original_status_code, original_content = original_response
        return PygeoapiResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )

    async def get_collection(
            self,
            *,
            collection_id: str,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> PygeoapiResponse:
        original_response = _describe_collections(
            self._pygeoapi_api,
            PygeoapiStarletteRequest(
                locale=locale,
                output_format=output_format,
            ),
            dataset=collection_id
        )
        original_headers, original_status_code, original_content = original_response
        return PygeoapiResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )

    async def list_collection_items(
            self,
            *,
            collection_id: str,
            bbox: str | None = None,
            bbox_crs: str | None = None,
            crs: str | None = None,
            datetime_filter: str | None = None,
            filter_: str | None = None,
            filter_crs: str | None = None,
            filter_lang: str | None = None,
            limit: int | None = None,
            locale: babel.Locale,
            offset: int = 0,
            output_format: Literal["json", "jsonld"] = "json",
            properties: dict | None = None,
            query_param: str | None = None,
            result_type: Literal["results"] | None = "results",
            sort_by: str | None = None,
            skip_geometry: bool = False,
    ) -> PygeoapiResponse:
        query_params = {
            k:v for k, v in {
                **properties,
                "bbox": bbox,
                "bbox-crs": bbox_crs,
                "crs": crs,
                "datetime": datetime_filter,
                "filter": filter_,
                "filter-crs": filter_crs,
                "filter-lang": filter_lang,
                "limit": limit,
                "offset": str(offset),
                "q": query_param,
                "resulttype": result_type,
                "sortby": sort_by,
                "skipGeometry": "true" if skip_geometry else "false",
            }.items()
            if v is not None
        }
        original_response = _get_collection_items(
            self._pygeoapi_api,
            PygeoapiStarletteRequest(
                locale=locale,
                output_format=output_format,
                **query_params
            ),
            dataset=collection_id
        )
        original_headers, original_status_code, original_content = original_response
        return PygeoapiResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )

    async def get_item(
            self,
            *,
            item_id: str,
            collection_id: str,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> PygeoapiResponse:
        original_response = _get_collection_item(
            self._pygeoapi_api,
            PygeoapiStarletteRequest(
                locale=locale,
                output_format=output_format,
            ),
            dataset=collection_id,
            identifier=item_id,
        )
        original_headers, original_status_code, original_content = original_response
        return PygeoapiResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )
