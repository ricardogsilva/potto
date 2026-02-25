import dataclasses
import logging
from typing import Any

import shapely
from starlette.datastructures import FormData
from starlette.requests import Request
from starlette_admin import (
    BaseField,
    RequestAction,
)

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SpatialExtentField(BaseField):
    display_template: str = "displays/spatial-extent.html"
    form_template: str = "forms/spatial-extent.html"

    async def parse_form_data(
            self,
            request: Request,
            form_data: FormData,
            action: RequestAction,
    ) -> shapely.Polygon | None:
        logger.debug(f"Processing form data: {form_data=}")
        if not (raw_value := form_data.get(self.name)):
            return None
        return shapely.from_wkt(raw_value)

    async def serialize_value(
        self, request: Request, value: Any, action: RequestAction
    ) -> Any:
        return value

    def dict(self) -> dict[str, Any]:
        return super().dict()

    def additional_css_links(
        self, request: Request, action: RequestAction
    ) -> list[str]:
        return [
            "https://unpkg.com/maplibre-gl@latest/dist/maplibre-gl.css"
        ]

    def additional_js_links(self, request: Request, action: RequestAction) -> list[str]:
        return [
            "https://unpkg.com/maplibre-gl@latest/dist/maplibre-gl.js"
        ]

