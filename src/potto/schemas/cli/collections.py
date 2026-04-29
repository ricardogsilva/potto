import datetime as dt

import pydantic

from ...schemas.base import CollectionType
from ...db.models import Collection, User


class CollectionListItem(pydantic.BaseModel):
    resource_identifier: str
    collection_type: CollectionType
    owner: str
    is_public: bool

    @classmethod
    def from_db_item(cls, item: Collection) -> "CollectionListItem":
        return cls(
            **item.model_dump(),
            owner=item.owner.username,
        )


class CollectionDetail(CollectionListItem):
    editors: list[str] = []
    viewers: list[str] = []
    created_at: dt.datetime
    updated_at: dt.datetime | None

    @classmethod
    def from_db_item(
        cls,
        item: Collection,
        editors: list[User] | None = None,
        viewers: list[User] | None = None,
    ) -> "CollectionDetail":
        return cls(
            **item.model_dump(),
            owner=item.owner.username,
            editors=[u.username for u in (editors or [])],
            viewers=[v.username for v in (viewers or [])],
        )
