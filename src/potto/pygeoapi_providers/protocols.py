from typing import Protocol


class PygeoapiFeatureProviderProtocol(Protocol):
    storage_crs: str
    editable: bool
    type: str = "feature"

    def __init__(self, provider_definition: dict) -> None: ...

    @property
    def fields(self) -> dict:
        """Return schema of public fields."""

    @property
    def properties(self) -> list[ReturnableProperty] | None: ...

    @property
    def id_field(self) -> str | None: ...

    @property
    def time_field(self) -> str | None: ...

    # def get_fields(self) -> dict:
    #     """Return schema of public fields."""

    def query(
            self,
            offset: int = 0,
            limit: int = 10,
            resulttype: Literal["hits", "results"] = "results",
            bbox: RawBbox | None = None,
            datetime_: RawDateTimeOrRange | None = None,
            properties: list[EqualityFilterableProperty] | None = None,
            sortby: list[SortByEntry] | None = None,
            select_properties: list[ReturnableProperty] | None = None,
            skip_geometry: bool = False,
            q: RawFullTextSearchQuery | None = None,
            filterq: CqlQueryText | None = None,
            crs_transform_spec: "CrsTransformSpec | None" = None,
    ) -> GeoJsonFeatureCollection:
        ...

    def get(
            self,
            identifier: str | int,
            crs_transform_spec: "CrsTransformSpec | None" = None,
            **kwargs
    ) -> GeoJsonFeature:
        ...
