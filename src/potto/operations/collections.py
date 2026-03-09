import logging

import shapely
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.authentication import BaseUser

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
        collection_type_filter: list[CollectionType] | None = None,
) -> list[Collection]:
    """List all collections that the user has access to."""
    return await collection_queries.collect_all_collections(
        session,
        collection_type_filter
    )


async def paginated_list_collections(
        session: AsyncSession,
        user: BaseUser,
        *,
        page: int = 1,
        page_size: int = 20,
        include_total: bool = False,
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
    provider_types = set([p.get("type") for p in pygeoapi_collection.get("providers", [])])
    collection_type_mapping = {
        "feature": CollectionType.FEATURE_COLLECTION,
        "record": CollectionType.RECORD_COLLECTION,
        "coverage": CollectionType.COVERAGE,
        # mapping provider 'map' to 'CollectionType.COVERAGE' is really an arbitrary mapping,
        # pygeoapi does not seem to know about the underlying type of data of a map
        "map": CollectionType.COVERAGE,
    }
    try:
        collection_type = collection_type_mapping[
            provider_types.intersection(set(collection_type_mapping)).pop()
        ]
    except (TypeError, KeyError) as err:
        raise PottoException(f"Unsupported collection type: {provider_types=}") from err

    resource_spatial_extents = pygeoapi_collection.get(
        "extents", {}).get("spatial", {})
    try:
        # TODO: support inspecting the CRS
        spatial_extent = shapely.box(*resource_spatial_extents.get("bbox"))
    except TypeError:
        spatial_extent = None
    providers = {}
    for prov in pygeoapi_collection.get("providers", []):
        if (type_ := prov.pop("type")) in providers.keys():
            continue
        providers[type_] = CollectionProvider(
            python_callable=prov.pop("name"),
            config=CollectionProviderConfiguration(
                data=prov.pop("data"),
                options=prov
            )
        )

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
