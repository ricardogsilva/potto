import logging

import shapely
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import (
    func,
    or_,
    select,
)

from ..models import CollectionResource
from .common import _get_total_num_records

logger = logging.getLogger(__name__)


async def paginated_list_collections(
        session: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        include_total: bool = False,
        identifier_filter: str | None = None,
        spatial_intersect: shapely.Polygon | None = None,
) -> tuple[list[CollectionResource], int | None]:
    limit = page_size
    offset = limit * (page - 1)
    return await list_collections(
        session,
        limit,
        offset,
        include_total,
        identifier_filter=identifier_filter,
        spatial_intersect=spatial_intersect,
    )


async def list_collections(
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        include_total: bool = False,
        identifier_filter: str | None = None,
        spatial_intersect: shapely.Polygon | None = None,
) -> tuple[list[CollectionResource], int | None]:
    statement = select(CollectionResource)
    if identifier_filter:
        statement = statement.where(
            CollectionResource.resource_identifier.ilike(f"%{identifier_filter}%")
        )
    if spatial_intersect is not None:
        statement = statement.where(
            or_(
                func.ST_Intersects(
                    CollectionResource.spatial_extent,
                    func.ST_GeomFromText(spatial_intersect.wkt, 4326),
                ),
                CollectionResource.spatial_extent.is_(None),
            )
        )
    statement = statement.order_by(
        CollectionResource.resource_identifier.desc().nullslast()
    )
    items = (await session.exec(statement.offset(offset).limit(limit))).all()
    num_total = (
        await _get_total_num_records(session, statement) if include_total else None
    )
    return items, num_total


async def collect_all_collections(
        session: AsyncSession,
) -> list[CollectionResource]:
    _, num_total = await list_collections(session, limit=1, include_total=True)
    items, _ = await list_collections(session, limit=num_total, include_total=False)
    return items


async def get_collection(
        session: AsyncSession,
        collection_id: int,
) -> CollectionResource | None:
    return await session.get(CollectionResource, collection_id)


async def get_collection_by_resource_identifier(
        session: AsyncSession,
        resource_identifier: str,
) -> CollectionResource | None:
    statement = select(CollectionResource).where(
        CollectionResource.resource_identifier == resource_identifier
    )
    return (await session.exec(statement)).first()
