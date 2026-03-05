import shapely
from sqlmodel import (
    func,
    or_,
    select,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import (
    CollectionItem,
    CollectionType,
)
from .common import _get_total_num_records


async def collect_all_collections(
        session: AsyncSession,
        collection_type_filter: list[CollectionType] | None = None,
) -> list[CollectionItem]:
    _, num_total = await list_collections(
        session,
        limit=1,
        collection_type_filter=collection_type_filter,
        include_total=True
    )
    items, _ = await list_collections(
        session,
        limit=num_total,
        collection_type_filter=collection_type_filter,
        include_total=False,
    )
    return items


async def paginated_list_collections(
        session: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        include_total: bool = False,
        identifier_filter: str | None = None,
        collection_type_filter: list[CollectionType] | None = None,
        spatial_intersect: shapely.Polygon | None = None,
) -> tuple[list[CollectionItem], int | None]:
    limit = page_size
    offset = limit * (page - 1)
    return await list_collections(
        session,
        limit=limit,
        offset=offset,
        include_total=include_total,
        identifier_filter=identifier_filter,
        collection_type_filter=collection_type_filter,
        spatial_intersect=spatial_intersect,
    )


async def list_collections(
        session: AsyncSession,
        *,
        limit: int = 20,
        offset: int = 0,
        include_total: bool = False,
        identifier_filter: str | None = None,
        collection_type_filter: list[CollectionType] | None = None,
        spatial_intersect: shapely.Polygon | None = None,
) -> tuple[list[CollectionItem], int | None]:
    statement = select(CollectionItem)
    if identifier_filter:
        statement = statement.where(
            CollectionItem.resource_identifier.ilike(f"%{identifier_filter}%")
        )
    if collection_type_filter:
        statement = statement.where(CollectionItem.collection_type in collection_type_filter)
    if spatial_intersect is not None:
        statement = statement.where(
            or_(
                func.ST_Intersects(
                    CollectionItem.spatial_extent,
                    func.ST_GeomFromText(spatial_intersect.wkt, 4326),
                ),
                CollectionItem.spatial_extent.is_(None),
            )
        )
    statement = statement.order_by(
        CollectionItem.resource_identifier.desc().nullslast()
    )
    items = (await session.exec(statement.offset(offset).limit(limit))).all()
    num_total = (
        await _get_total_num_records(session, statement) if include_total else None
    )
    return items, num_total


async def get_collection(
        session: AsyncSession,
        collection_id: int,
) -> CollectionItem | None:
    return await session.get(CollectionItem, collection_id)


async def get_collection_by_resource_identifier(
        session: AsyncSession,
        resource_identifier: str,
) -> CollectionItem | None:
    statement = select(CollectionItem).where(CollectionItem.resource_identifier == resource_identifier)
    return (await session.exec(statement)).first()
