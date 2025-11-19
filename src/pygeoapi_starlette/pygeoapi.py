import dataclasses
import json
from typing import (
    Callable,
    Literal,
)

import babel
from pygeoapi.api import (
    API as _API,
    landing_page as _landing_page,
    conformance as _conformance,
    F_JSON,
    F_JSONLD,
    FORMAT_TYPES as _FORMAT_TYPES,
)
from pygeoapi.openapi import get_oas_30
from pygeoapi.l10n import translate_struct

from . import config
from .webapp.requests import PygeoapiStarletteRequest


@dataclasses.dataclass(frozen=True)
class PygeoapiStarletteResponse:
    content_type: str
    content: dict | bytes
    metadata: dict [str, str] | None = None


class PygeoapiStarlette:
    """A wrapper around pygeoapi core"""
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
    ) -> PygeoapiStarletteResponse:
        original_response = _landing_page(
            self._pygeoapi_api,
            PygeoapiStarletteRequest(
                locale=locale,
                output_format=output_format,
            )

        )
        original_headers, original_status_code, original_content = original_response
        return PygeoapiStarletteResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )

    async def get_conformance_details(
            self,
            *,
            locale: babel.Locale,
            output_format: Literal["json", "jsonld"] = "json"
    ) -> PygeoapiStarletteResponse:
        original_response = _conformance(
            self._pygeoapi_api,
            PygeoapiStarletteRequest(
                locale=locale,
                output_format=output_format,
            )
        )
        original_headers, original_status_code, original_content = original_response
        return PygeoapiStarletteResponse(
            content_type=original_headers.pop("Content-Type"),
            content=json.loads(original_content),
            metadata={**original_headers}
        )

    async def get_openapi_document(
            self,
    ) -> PygeoapiStarletteResponse:
        return PygeoapiStarletteResponse(
            content_type=_FORMAT_TYPES[F_JSON],
            content=self._pygeoapi_api.openapi
        )
