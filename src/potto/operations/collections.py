import copy
import logging

import shapely
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.authentication import BaseUser

from .. import util
from ..db.models import (
    Collection,
    User,
)
from ..db.commands import collections as collection_commands
from ..db.queries import collections as collection_queries
from ..exceptions import PottoException
from ..schemas.base import (
    CollectionProvider,
    CollectionProviderConfiguration,
    CollectionType,
)
from ..schemas.collections import (
    CollectionCreate,
    CollectionUpdate,
)

logger = logging.getLogger(__name__)


async def collect_all_collections(
        session: AsyncSession,
        user: BaseUser,
        is_public_filter: bool | None = True,
        collection_type_filter: list[CollectionType] | None = None,
) -> list[Collection]:
    """List all collections that the user has access to."""
    return await collection_queries.collect_all_collections(
        session,
        collection_type_filter=collection_type_filter,
        is_public_filter=is_public_filter,
    )


async def paginated_list_collections(
        session: AsyncSession,
        user: BaseUser,
        *,
        page: int = 1,
        page_size: int = 20,
        include_total: bool = False,
        is_public_filter: bool | None = True,
        identifier_filter: str | None = None,
        collection_type_filter: list[CollectionType] | None = None,
        spatial_intersect: shapely.Polygon | None = None,
) -> tuple[list[Collection], int | None]:
    """Produce a paginated list of all collections that the user has access to."""
    return await collection_queries.paginated_list_collections(
        session,
        page=page,
        page_size=page_size,
        include_total=include_total,
        identifier_filter=identifier_filter,
        is_public_filter=is_public_filter,
        collection_type_filter=collection_type_filter,
        spatial_intersect=spatial_intersect
    )


async def get_collection(
        session: AsyncSession,
        user: BaseUser,
        collection_id: int,
) -> Collection | None:
    return await collection_queries.get_collection(session, collection_id)


async def get_collection_by_resource_identifier(
        session: AsyncSession,
        user: BaseUser,
        identifier: str,
) -> Collection | None:
    return await collection_queries.get_collection_by_resource_identifier(session, identifier)


async def create_collection(
        session: AsyncSession,
        to_create: CollectionCreate,
) -> Collection:
    return await collection_commands.create_collection(session, to_create)


async def delete_collection(
        session: AsyncSession, user: BaseUser, collection_id: int) -> None:
    return await collection_commands.delete_collection(session, collection_id)


async def import_pygeoapi_collection(
        session: AsyncSession,
        user: User,
        identifier: str,
        pygeoapi_collection: dict,
        *,
        overwrite: bool = False,
) -> Collection:
    existing_db_collection = await collection_queries.get_collection_by_resource_identifier(
        session, identifier)
    if existing_db_collection and not overwrite:
        raise PottoException(f"Collection {identifier!r} already exists!")
    resource_spatial_extents = pygeoapi_collection.get(
        "extents", {}).get("spatial", {})
    try:
        # TODO: support inspecting the CRS
        spatial_extent = shapely.box(*resource_spatial_extents.get("bbox"))
    except TypeError:
        spatial_extent = None
    providers = {}
    for prov in pygeoapi_collection.get("providers", []):
        modifiable_prov = copy.deepcopy(prov)
        if (type_ := modifiable_prov.pop("type")) in providers.keys():
            continue
        providers[type_] = CollectionProvider(
            python_callable=modifiable_prov.pop("name"),
            config=CollectionProviderConfiguration(
                data=modifiable_prov.pop("data"),
                options=modifiable_prov
            )
        )

    collection_type = util.get_collection_type(pygeoapi_collection)
    if existing_db_collection and overwrite:
        # TODO: check if user is allowed to modify it
        logger.debug(f"Updating existing collection {identifier!r}...")
        to_update = CollectionUpdate(
            collection_type=collection_type,
            title=pygeoapi_collection.get("title", ""),
            description=pygeoapi_collection.get("description"),
            keywords=pygeoapi_collection.get("keywords"),
            spatial_extent=spatial_extent,
            temporal_extent_begin=pygeoapi_collection.get("extents", {}).get("temporal", {}).get("begin"),
            temporal_extent_end=pygeoapi_collection.get("extents", {}).get("temporal", {}).get("end"),
            additional_links=pygeoapi_collection.get("links"),
            providers=providers
        )
        return await collection_commands.update_collection(session, existing_db_collection, to_update)
    else:
        to_create = CollectionCreate(
            resource_identifier=identifier,
            owner_id=user.id,
            collection_type=collection_type,
            title=pygeoapi_collection.get("title", ""),
            description=pygeoapi_collection.get("description"),
            keywords=pygeoapi_collection.get("keywords"),
            spatial_extent=spatial_extent,
            temporal_extent_begin=pygeoapi_collection.get("extents", {}).get("temporal", {}).get("begin"),
            temporal_extent_end=pygeoapi_collection.get("extents", {}).get("temporal", {}).get("end"),
            additional_links=pygeoapi_collection.get("links"),
            providers=providers
        )
        return await create_collection(session, to_create)
