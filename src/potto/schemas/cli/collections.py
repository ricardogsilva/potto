import datetime as dt

import pydantic

from ...constants import CollectionType
from ..auth import PottoUser
from ..collections import Collection
from .. import base


class SimplifiedFeatureCollectionCreate(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    resource_identifier: base.CollectionIdentifier
    english_title: str
    provider: base.PottoProvider
    spatial_extent: base.MaybeShapelyGeometry = None
    is_public: bool = False


class CollectionListItem(pydantic.BaseModel):
    resource_identifier: str
    collection_type: CollectionType
    owner: str
    is_public: bool

    @classmethod
    def from_potto(cls, item: Collection) -> "CollectionListItem":
        return cls(
            resource_identifier=item.identifier,
            collection_type=item.type_,
            owner=item.owner.username,
            is_public=item.is_public,
        )


class CollectionDetail(CollectionListItem):
    title: str | dict[str, str]
    editors: list[str] = []
    viewers: list[str] = []
    created_at: dt.datetime
    updated_at: dt.datetime | None
    spatial_extent: str | None

    @classmethod
    def from_potto(
        cls,
        item: Collection,
        editors: list[PottoUser] | None = None,
        viewers: list[PottoUser] | None = None,
    ) -> "CollectionDetail":
        return cls(
            resource_identifier=item.identifier,
            collection_type=item.type_,
            owner=item.owner.username,
            is_public=item.is_public,
            title=item.title,
            editors=[u.username for u in (editors or [])],
            viewers=[v.username for v in (viewers or [])],
            created_at=item.created_at,
            updated_at=item.updated_at,
            spatial_extent=str(item.spatial_extent) if item.spatial_extent else None,
        )
