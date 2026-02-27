import datetime as dt
import pydantic


class ItemCollectionConfigReadListItem(pydantic.BaseModel):
    identifier: str


class ItemCollectionConfigRead(ItemCollectionConfigReadListItem):
    title: str | dict[str, str]
    type_: str
    description: str | dict[str, str]
    keywords: list[str] | dict[str, list[str]]
    visibility: str
    linked_data: dict | None


class ItemCollectionConfigCreate(pydantic.BaseModel):
    identifier: str
    title: str
    description: str | None = None
    keywords: list[str] | None = None
    spatial_extent: tuple[float, float, float, float] | None = None
    temporal_extent_begin: dt.datetime | None = None
    temporal_extent_end: dt.datetime | None = None
    provider: dict| None = None
