import pydantic

from ...db.models import Collection


class CollectionListItem(pydantic.BaseModel):
    resource_identifier: str

    @classmethod
    def from_db_item(cls, item: Collection) ->"CollectionListItem":
        return cls(**item.model_dump())


class CollectionDetail(pydantic.BaseModel):
    resource_identifier: str

    @classmethod
    def from_db_item(cls, item: Collection) ->"CollectionDetail":
        return cls(**item.model_dump())


class CollectionListMeta(pydantic.BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class CollectionList(pydantic.BaseModel):
    items: list[CollectionListItem]
    meta: CollectionListMeta
