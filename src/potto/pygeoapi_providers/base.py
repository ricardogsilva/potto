from typing import (
    NewType,
    TypedDict,
)


class SortByEntry(TypedDict):
    property: str
    order: str


CqlQueryText = NewType("CqlQueryText", str)
EqualityFilterableProperty = NewType("EqualityFilterableProperty", tuple[str, str])
GeoJsonFeature = NewType("GeoJsonFeature", dict)
GeoJsonFeatureCollection = NewType("GeoJsonFeatureCollection", dict)
RawBbox = NewType("RawBbox", list[int | float])
RawDateTimeOrRange = NewType("RawDateTimeOrRange", str)
RawFullTextSearchQuery = NewType("RawFullTextSearchQuery", str)
ReturnableProperty = NewType("ReturnableProperty", str)
