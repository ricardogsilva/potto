import shapely
from sqlalchemy.orm import selectinload
from sqlmodel import (
    func,
    or_,
    select,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import (
    Collection,
    CollectionType,
    User,
)
from .common import _get_total_num_records


async def collect_all_collections(
        session: AsyncSession,
        collection_type_filter: list[CollectionType] | None = None,
        is_public_filter: bool | None = True,
        user_id: str | None = None,
        accessible_identifiers: list[str] | None = None,
) -> list[Collection]:
    _, num_total = await list_collections(
        session,
        limit=1,
        collection_type_filter=collection_type_filter,
        is_public_filter=is_public_filter,
        user_id=user_id,
        accessible_identifiers=accessible_identifiers,
        include_total=True
    )
    items, _ = await list_collections(
        session,
        limit=num_total,
        collection_type_filter=collection_type_filter,
        is_public_filter=is_public_filter,
        user_id=user_id,
        accessible_identifiers=accessible_identifiers,
        include_total=False,
    )
    return items


async def paginated_list_collections(
        session: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        include_total: bool = False,
        is_public_filter: bool | None = True,
        user_id: str | None = None,
        accessible_identifiers: list[str] | None = None,
        identifier_filter: str | None = None,
        collection_type_filter: list[CollectionType] | None = None,
        spatial_intersect: shapely.Polygon | None = None,
) -> tuple[list[Collection], int | None]:
    limit = page_size
    offset = limit * (page - 1)
    return await list_collections(
        session,
        limit=limit,
        offset=offset,
        include_total=include_total,
        is_public_filter=is_public_filter,
        user_id=user_id,
        accessible_identifiers=accessible_identifiers,
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
        is_public_filter: bool | None = True,
        user_id: str | None = None,
        accessible_identifiers: list[str] | None = None,
        identifier_filter: str | None = None,
        collection_type_filter: list[CollectionType] | None = None,
        spatial_intersect: shapely.Polygon | None = None,
) -> tuple[list[Collection], int | None]:
    statement = select(Collection).options(selectinload(Collection.owner))
    if user_id is not None:
        statement = statement.where(
            or_(
                Collection.is_public == True,
                Collection.owner_id == user_id,
                Collection.resource_identifier.in_(accessible_identifiers or []),
            )
        )
    elif is_public_filter is not None:
        statement = statement.where(Collection.is_public == is_public_filter)
    if identifier_filter:
        statement = statement.where(
            Collection.resource_identifier.ilike(f"%{identifier_filter}%")
        )
    if collection_type_filter:
        statement = statement.where(Collection.collection_type in collection_type_filter)
    if spatial_intersect is not None:
        statement = statement.where(
            or_(
                func.ST_Intersects(
                    Collection.spatial_extent,
                    func.ST_GeomFromText(spatial_intersect.wkt, 4326),
                ),
                Collection.spatial_extent.is_(None),
            )
        )
    statement = statement.order_by(
        Collection.resource_identifier.desc().nullslast()
    )
    items = (await session.exec(statement.offset(offset).limit(limit))).all()
    num_total = (
        await _get_total_num_records(session, statement) if include_total else None
    )
    return items, num_total


async def get_collection(
        session: AsyncSession,
        collection_id: int,
) -> Collection | None:
    statement = (
        select(Collection)
        .options(selectinload(Collection.owner))
        .where(Collection.id == collection_id)
    )
    return (await session.exec(statement)).first()


async def get_collection_editors(
        session: AsyncSession,
        resource_identifier: str,
) -> list[User]:
    statement = select(User).where(
        User.scopes.contains([f"collection-{resource_identifier}:editor"])
    )
    return list((await session.exec(statement)).all())


async def get_collection_viewers(
        session: AsyncSession,
        resource_identifier: str,
) -> list[User]:
    statement = select(User).where(
        User.scopes.contains([f"collection-{resource_identifier}:viewer"])
    )
    return list((await session.exec(statement)).all())


async def get_collection_by_resource_identifier(
        session: AsyncSession,
        resource_identifier: str,
) -> Collection | None:
    statement = (
        select(Collection)
        .options(selectinload(Collection.owner))
        .where(Collection.resource_identifier == resource_identifier)
    )
    return (await session.exec(statement)).first()
