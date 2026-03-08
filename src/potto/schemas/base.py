import enum
import typing
import pydantic

import shapely
from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape

from .. import constants

if typing.TYPE_CHECKING:
    from .pygeoapi_config import ExtentConfig


def _serialize_localizable_field(value: dict[str, str] | str, _info):
    """Serialize a localizable field.

    Localizable fields use a JSONB type, which is not serialized by default, hence
    the need for this function.
    """
    return value


def _serialize_localizable_list_field(value: dict[str, list[str]] | list[str], _info):
    """Serialize a localizable list field.

    Localizable fields use a JSONB type, which is not serialized by default, hence
    the need for this function.
    """
    return value


def to_shapely(
        value: str | WKBElement | shapely.Geometry | None
) -> shapely.Geometry | None:
    if not value:
        return None
    elif isinstance(value, shapely.Geometry):
        return value
    elif isinstance(value, str):
        return shapely.from_wkt(value)
    else:
        return to_shape(value)


MaybeShapelyGeometry = typing.Annotated[
    shapely.Geometry | None,
    pydantic.BeforeValidator(to_shapely),
    pydantic.PlainSerializer(
        lambda geom: shapely.to_geojson(geom) if geom else None,
        return_type=str
    ),
]


class CollectionType(str, enum.Enum):
    COVERAGE = "coverage"
    FEATURE_COLLECTION = "feature_collection"
    RECORD_COLLECTION = "record_collection"


class PygeoapiProviderType(str, enum.Enum):
    COVERAGE = "coverage"
    EDR = "edr"
    FEATURE = "feature"
    MAP = "map"
    RECORD = "record"
    STAC = "stac"
    TILE = "tile"


Title = typing.Annotated[
    dict[str, str] | str,
    pydantic.PlainSerializer(_serialize_localizable_field)
]
MaybeDescription = typing.Annotated[
    dict[str, str] | str | None,
    pydantic.PlainSerializer(_serialize_localizable_field)
]
MaybeKeywords = typing.Annotated[
    dict[str, list[str]] | list[str] | None,
    pydantic.PlainSerializer(_serialize_localizable_list_field)
]


class Link(pydantic.BaseModel):
    media_type: str = pydantic.Field(alias="type")
    rel: str
    href: str
    title: str | None = None
    href_lang: str | None = None
    length: int | None = None


class TwoDimensionalSpatialExtent(pydantic.BaseModel):
    bbox: list[tuple[float, float, float, float]]
    crs: str = constants.CRS_84


class ThreeDimensionSpatialExtent(pydantic.BaseModel):
    bbox: list[tuple[float, float, float, float, float, float]]
    crs: str = constants.CRS_84h


class TemporalExtent(pydantic.BaseModel):
    interval: list[tuple[str | None, str | None]]
    trs: str = constants.GREGORIAN


class Extent(pydantic.BaseModel):
    spatial: TwoDimensionalSpatialExtent | ThreeDimensionSpatialExtent | None = None
    temporal : TemporalExtent | None = None

    @classmethod
    def from_config(cls, extent_config: "ExtentConfig") -> "Extent":
        if extent_config.temporal:
            temporal_conf = {
                "interval": [
                    (
                        begin.strftime("%Y-%m-%DT%H:%M:%SZ") if (begin := extent_config.temporal.begin) else None,
                        end.strftime("%Y-%m-%DT%H:%M:%SZ") if (end := extent_config.temporal.end) else None
                    )
                ],
                "trs": extent_config.temporal.trs
            }
        else:
            temporal_conf = None

        return cls(
            spatial={
                "bbox": [extent_config.spatial.bbox],
                "crs": extent_config.spatial.crs,
            },
            temporal=temporal_conf
        )


class CollectionProviderConfiguration(pydantic.BaseModel):
    data: str | dict
    options: dict[str, typing.Any]


class CollectionProvider(pydantic.BaseModel):
    python_callable: str
    config: CollectionProviderConfiguration | None = None


class PaginationContext(pydantic.BaseModel):
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
