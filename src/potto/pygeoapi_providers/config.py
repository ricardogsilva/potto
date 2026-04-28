
import logging
from typing import (
    Literal,
    TYPE_CHECKING

)

if TYPE_CHECKING:
    from pygeoapi.crs import CrsTransformSpec

from pygeoapi.provider.base import ProviderItemNotFoundError

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

logger = logging.getLogger(__name__)


class PygeoapiConfigGeoJsonProvider:
    _fields: dict[str, dict[str, str]]
    _data: dict[GeoJsonFeature]

    editable: bool = False
    id_field: str | None = None
    properties: list[ReturnableProperty]
    time_field: str | None = None
    type: str = "feature"

    def __init__(self, provider_definition: dict) -> None:
        """Pygeoapi provider that stores data directly in the configuration object.

        This is mainly useful for testing.
        """
        self._data = {feat["id"]: feat for feat in provider_definition["data"].get("features", [])}
        try:
            first_feature = next(iter(self._data.values()))
        except StopIteration:
            self.properties = []
            self._fields = {}
            return
        field_names = set(first_feature["properties"].keys())
        returnable = provider_definition.get("properties") or []
        if returnable:
            field_names = field_names.intersection(returnable)
        self.properties = list(field_names)
        field_schema = {}
        for name, value in first_feature["properties"].items():
            if name not in self.properties:
                continue
            value_type = type(value).__name__
            try:
                schema_type = {
                    "float": "number",
                    "int": "integer",
                    "bool": "boolean",
                    "str": "string",
                }[value_type]
            except KeyError:
                logger.warning(f"Ignoring unsupported type {value_type}")
                continue
            field_schema[name] = {"type": schema_type}
        self._fields = field_schema

    @property
    def fields(self) -> dict:
        return self._fields.copy()

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
        return {
            "type": "FeatureCollection",
            "features": list(self._data.values())
        }

    def get(
            self,
            identifier: str | int,
            crs_transform_spec: "CrsTransformSpec | None" = None,
            **kwargs
    ) -> GeoJsonFeature:
        try:
            return self._data[identifier].copy()
        except KeyError as err:
            raise ProviderItemNotFoundError(f"Item {identifier!r} not found") from err
