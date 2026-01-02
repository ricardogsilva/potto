import typing
import pydantic

from .. import constants

if typing.TYPE_CHECKING:
    from .pygeoapi_config import ExtentConfig


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
