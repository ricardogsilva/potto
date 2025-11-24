from typing import (
    Literal,
    Mapping,
    Sequence,
)
import pydantic


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
            result_type=params.get("resulttype"),
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
    id_: str
    properties: dict[str, str]
    geometry_wkt: str

    @classmethod
    def from_original_feature(cls, original_feature: dict) -> "Feature":
        return cls(
            id_=original_feature["id"],
            properties=original_feature["properties"],
            geometry_wkt=original_feature["geometry"],
        )


class FeatureList(pydantic.BaseModel):
    features: list[Feature]
    feature_title_field: str
    number_matched: int
    number_returned: int
    number_total: int
    timestamp: str


class RecordList(pydantic.BaseModel):
    ...
