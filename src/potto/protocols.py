import typing

import shapely
from starlette.authentication import BaseUser

if typing.TYPE_CHECKING:
    from .config import PottoSettings
    from .schemas.base import CollectionType
    from .schemas.potto import (
        Collection,
        CollectionList,
        ServerMetadata,
    )


class CollectionRetrieverProtocol(typing.Protocol):
    """Protocol for a callable that can be used by Potto to get collections."""

    async def get_collection(
            self,
            settings: "PottoSettings",
            *,
            collection_identifier: str,
            user: BaseUser,
    ) -> "Collection | None": ...

    async def list_collections(
            self,
            settings: "PottoSettings",
            *,
            user: BaseUser,
            page: int = 1,
            page_size: int = 20,
            include_total: bool = False,
            identifier_filter: str | None = None,
            collection_type_filter: list["CollectionType"] | None = None,
            spatial_intersect: shapely.Polygon | None = None,
    ) -> "CollectionList": ...


class ServerMetadataRetrieverProtocol(typing.Protocol):

    def __call__(self, settings: "PottoSettings") -> "ServerMetadata": ...