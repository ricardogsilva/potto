import shapely
from starlette.authentication import BaseUser

from .config import PottoSettings
from .operations import collections as collection_ops
from .schemas.base import CollectionType
from .schemas.potto import (
    Collection,
    CollectionList,
    Pagination,
)


class DbCollectionRetriever:

    @classmethod
    async def get_collection(
            cls,
            settings: PottoSettings,
            *,
            collection_identifier: str,
            user: BaseUser,
    ) -> Collection | None:
        async with settings.get_db_session_maker()() as session:
            db_collection = await collection_ops.get_collection_by_resource_identifier(
                session,
                identifier=collection_identifier,
            )
            return Collection(**db_collection.model_dump()) if db_collection else None

    @classmethod
    async def list_collections(
            cls,
            settings: PottoSettings,
            *,
            user: BaseUser,
            page: int = 1,
            page_size: int = 20,
            include_total: bool = False,
            identifier_filter: str | None = None,
            collection_type_filter: list[CollectionType] | None = None,
            spatial_intersect: shapely.Polygon | None = None,
    ) -> CollectionList:
        async with settings.get_db_session_maker()() as session:
            db_collections, total = await collection_ops.paginated_list_collections(
                session,
                user=user,
                page=page,
                page_size=page_size,
                include_total=include_total,
                identifier_filter=identifier_filter,
                collection_type_filter=collection_type_filter,
                spatial_intersect=spatial_intersect,
            )
            return CollectionList(
                collections=[Collection(**db_col.model_dump()) for db_col in db_collections],
                pagination=Pagination(
                    page=page,
                    page_size=len(db_collections),
                    total=total
                )
            )