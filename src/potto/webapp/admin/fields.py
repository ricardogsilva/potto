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
        logger.debug(f"{form_data=}")
        min_lon = form_data.get(f"{self.id}-min-lon")
        max_lon = form_data.get(f"{self.id}-max-lon")
        min_lat = form_data.get(f"{self.id}-min-lat")
        max_lat = form_data.get(f"{self.id}-max-lat")
        logger.debug(f"{min_lon=}, {max_lon=}, {min_lat=}, {max_lat=}")
        if not all((min_lon, max_lon, min_lat, max_lat)):
            return None
        min_lon = float(min_lon)
        max_lon = float(max_lon)
        min_lat = float(min_lat)
        max_lat = float(max_lat)
        x_min = min(min_lon, max_lon)
        x_max = max(min_lon, max_lon)
        y_min = min(min_lat, max_lat)
        y_max = max(min_lat, max_lat)
        bbox = shapely.box(x_min, y_min, x_max, y_max)
        logger.debug(f"{bbox=}")
        return bbox

    async def serialize_value(
        self, request: Request, value: shapely.Polygon | None, action: RequestAction
    ) -> str | None:
        logger.debug(f"{value=} - {type(value)=}")
        return shapely.to_geojson(value) if value else None

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
            "https://unpkg.com/maplibre-gl@latest/dist/maplibre-gl.js",
            "https://unpkg.com/terra-draw@1.0.0/dist/terra-draw.umd.js",
            "https://unpkg.com/terra-draw-maplibre-gl-adapter@1.0.0/dist/terra-draw-maplibre-gl-adapter.umd.js"
        ]

