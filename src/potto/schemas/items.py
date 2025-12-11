import json
import logging
from typing import (
    Any,
    Literal,
    Mapping,
    Protocol,
    Sequence,
)

import pydantic
import shapely
from starlette.datastructures import URL

from . import pygeoapi_config

logger = logging.getLogger(__name__)


class UrlResolver(Protocol):

    def __call__(self, route: str, /, **path_param: Any) -> URL:
        ...


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

    def as_geojson(self) -> dict:
        return {
            **self.model_dump(
                exclude={
                    "geometry",
                }
            ),
            "geometry": json.loads(shapely.to_geojson(self.geometry))
        }

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


class FeatureList(pydantic.BaseModel):
    features: list[Feature]
    feature_title_field: str
    number_matched: int
    number_returned: int
    timestamp: str


class RecordList(pydantic.BaseModel):
    ...
