import pydantic

from ...schemas.base import CollectionType
from ...db.models import Collection


class CollectionListItem(pydantic.BaseModel):
    resource_identifier: str
    collection_type: CollectionType

    @classmethod
    def from_db_item(cls, item: Collection) ->"CollectionListItem":
        return cls(**item.model_dump())


class CollectionDetail(CollectionListItem):
    resource_identifier: str

    @classmethod
    def from_db_item(cls, item: Collection) ->"CollectionDetail":
        return cls(**item.model_dump())
