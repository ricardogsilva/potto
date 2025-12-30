import pydantic

from .. import constants


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
