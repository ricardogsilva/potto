import json
import logging
from typing import (
    Literal,
    Mapping,
    Sequence,
)

import pydantic
import shapely
from pygeoapi.api import (
    F_JSON,
    FORMAT_TYPES,
)

from ..webapp.protocols import UrlResolver
from . import pygeoapi_config
from .base import Link

logger = logging.getLogger(__name__)


class CollectionFilter(pydantic.BaseModel):
    bbox: str | None = None
    bbox_crs: str | None = None
    cql_text: str | None = None
    datetime_: str | None = None
    extra_properties: dict[str, str] | None = None
    filter_: str | None = None
    filter_lang: str | None = None
    filter_crs_uri: str | None = None
    limit: int = 20
    locale: str | None = None
    offset: int = 0
    query: str | None = None
    result_type: Literal["hits", "results"] = "results"
    select_properties: list[str] | None = None
    skip_geometry: bool | None = None
    sort_by: str | None = None


class FeatureCollectionFilter(CollectionFilter):
    crs: str | None = None

    @classmethod
    def from_query_parameters(
            cls,
            params: Mapping[str, str | Sequence[str]],
    ) -> "FeatureCollectionFilter":
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

    def as_kwargs(self) -> dict:
        return {
            k: v for k, v in {
                **self.extra_properties,
                "bbox": self.bbox,
                "bbox-crs": self.bbox_crs,
                "crs": self.crs,
                "datetime": self.datetime_,
                "filter": self.filter_,
                "filter-crs": self.filter_crs_uri,
                "filter-lang": self.filter_lang,
                "limit": self.limit,
                "offset": str(self.offset),
                "q": self.query,
                "resulttype": self.result_type,
                "sortby": self.sort_by,
                "skipGeometry": "true" if self.skip_geometry else "false",
            }.items()
            if v is not None
        }


class FeatureCollectionPaginationContext(pydantic.BaseModel):
    limit: int
    number_matched: int
    number_returned: int
    offset: int

    def get_links(
            self,
            base_url: str,
            target_media_type: str = F_JSON,
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

    def as_geojson(
            self,
            resource_config: pygeoapi_config.ItemCollectionConfig,
            url_resolver: UrlResolver,
            detail_link_format: str = F_JSON
    ) -> dict:
        serialized = {
            **self.model_dump(
                by_alias=True,
                exclude={
                    "geometry",
                }
            ),
            "type": "Feature",
            "geometry": json.loads(shapely.to_geojson(self.geometry)),
        }
        serialized["properties"]["links"] = [
            Link(
                type=FORMAT_TYPES.get(detail_link_format, F_JSON),
                rel="detail",
                href=str(
                    url_resolver(
                        "get-item",
                        collection_id=resource_config.identifier,
                        item_id=self.id_
                    )
                ),
                title="This feature's detail",
            ).model_dump(exclude_none=True)
        ]
        return serialized

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
