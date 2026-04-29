from typing import (
    Literal,
    Protocol,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from pygeoapi.crs import CrsTransformSpec

from .base import (
    CqlQueryText,
    EqualityFilterableProperty,
    GeoJsonFeature,
    GeoJsonFeatureCollection,
    RawBbox,
    RawDateTimeOrRange,
    RawFullTextSearchQuery,
    ReturnableProperty,
    SortByEntry,
)


class PygeoapiReadOnlyFeatureProviderProtocol(Protocol):
    editable: Literal[False]
    storage_crs: str
    type: Literal["feature"]
    include_extra_query_parameters: bool
    id_field: str | None
    time_field: str | None
    uri_field: str | None

    def __init__(self, provider_definition: dict) -> None: ...

    @property
    def fields(self) -> dict:
        """Return schema of public fields."""

    @property
    def properties(self) -> list[ReturnableProperty] | None: ...

    def query(
        self,
        offset: int = 0,
        limit: int = 10,
        resulttype: Literal["hits", "results"] = "results",
        bbox: RawBbox | None = None,
        datetime_: RawDateTimeOrRange | None = None,
        properties: list[EqualityFilterableProperty] | None = None,
        sortby: list[SortByEntry] | None = None,
        skip_geometry: bool = False,
        select_properties: list[ReturnableProperty] | None = None,
        crs_transform_spec: "CrsTransformSpec | None" = None,
        q: RawFullTextSearchQuery | None = None,
        language: str | None = None,
        filterq: CqlQueryText | None = None,
    ) -> GeoJsonFeatureCollection: ...

    def get(
        self,
        identifier: str | int,
        crs_transform_spec: "CrsTransformSpec | None" = None,
        **kwargs,
    ) -> GeoJsonFeature: ...
