import json
import logging
from typing import (
    Annotated,
    Literal,
    Mapping,
    Sequence,
)

import pydantic
import shapely
from pygeoapi.api import F_JSON

from .. import constants
from ..webapp.protocols import UrlResolver
from . import pygeoapi_config
from .base import (
    Extent,
    Link,
)

logger = logging.getLogger(__name__)


class Collection(pydantic.BaseModel):
    id_: Annotated[str, pydantic.Field(alias="id")]
    title: str | None = None
    description: str | None = None
    extent: Extent | None = None
    item_type: Annotated[str, pydantic.Field(alias="itemType")] | None = "feature"
    crs: list[str] = pydantic.Field(default_factory=lambda : [constants.CRS_84])


class ItemFilter(pydantic.BaseModel):
    bbox: str | None = None
    bbox_crs: Annotated[str | None, pydantic.Field(alias="bbox-crs")] = None
    cql_text: str | None = None
    datetime_: Annotated[str | None, pydantic.Field(alias="datetime")] = None
    extra_properties: dict[str, str] | None = None
    filter_: Annotated[str | None, pydantic.Field(alias="filter")] = None
    filter_lang: str | None = None
    filter_crs_uri: str | None = None
    limit: int = 20
    locale: Annotated[str | None, pydantic.Field(alias="language")] = None
    offset: int = 0
    query: str | None = None
    result_type: Literal["hits", "results"] = "results"
    select_properties: Annotated[list[str] | None, pydantic.Field(alias="properties")] = None
    skip_geometry: Annotated[bool | None, pydantic.Field(alias="skipGeometry")] = None
    sort_by: Annotated[str | None, pydantic.Field(alias="sortby")] = None


class FeatureFilter(ItemFilter):
    crs: str | None = None

    @classmethod
    def from_query_parameters(
            cls,
            params: Mapping[str, str | Sequence[str]],
    ) -> "FeatureFilter":
        return cls(
            bbox=params.get("bbox"),
            bbox_crs=params.get("bbox-crs"),
            crs=params.get("crs"),
            datetime_=params.get("datetime"),
            filter_=params.get("filter"),
            filter_crs_uri=params.get("filter-crs"),
            filter_lang=params.get("filter-lang"),
            limit=int(params.get("limit", 20)),
            offset=int(params.get("offset", 0)),
            extra_properties=dict(params),
            query=params.get("q"),
            result_type=params.get("resulttype", "results"),
            sort_by=params.get("sortby"),
            skip_geometry=(
                True
                if params.get("skipGeometry", "").lower()
                   in ("true", "yes", "on", "t", "1") else False
            ),
        )


class CollectionItemsPaginationContext(pydantic.BaseModel):
    limit: int
    number_matched: int
    number_returned: int
    offset: int

    def get_links(
            self,
            base_url: str,
            target_media_type: str = constants.MEDIA_TYPE_JSON,
            additional_query_params: dict[str, str] | None = None,
    ) -> list[Link]:
        additional = "&".join(f"{k}={v}" for k, v in additional_query_params.items())
        result = []
        if self.offset > 0:
            prev_offset = max(0, self.offset - self.limit)
            result.append(
                Link(
                    type=target_media_type,
                    rel="prev",
                    href=f"{base_url}?offset={prev_offset}{f'&{additional}' if additional else ''}",
                    title="Previous page of this resultset"
                )
            )
        if self.number_matched > self.offset + self.limit:
            next_offset = self.offset + self.limit
            result.append(
                Link(
                    type=target_media_type,
                    rel="next",
                    href=f"{base_url}?offset={next_offset}{f'&{additional}' if additional else ''}",
                    title="Next page of this resultset"
                )
            )
        return result


class Feature(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True
    )

    id_: str = pydantic.Field(alias="id")
    properties: dict[str, str | int | float | bool]
    geometry: shapely.Geometry

    @classmethod
    def from_original_feature(cls, original_feature: dict) -> "Feature":
        return cls(
            id=str(original_feature["id"]),
            properties={k: v for k, v in original_feature["properties"].items() if k != "id"},
            geometry=shapely.from_geojson(json.dumps(original_feature["geometry"]))
        )

    def as_jsonld(
            self,
            resource_config: pygeoapi_config.ItemCollectionConfig,
            url_resolver: UrlResolver
    ) -> dict:
        detail_url = url_resolver(
            "get-item",
            collection_id=resource_config.identifier,
            item_id=self.id_
        )
        return {
            "@type": "schema:Place",
            "@id": str(detail_url),
        }
