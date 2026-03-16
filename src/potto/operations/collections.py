import copy
import logging

import shapely
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.authentication import BaseUser

from .. import util
from ..authz.base import AuthorizationBackendProtocol
from ..db.models import (
    Collection,
    User,
)
from ..db.commands import (
    auth as auth_commands,
    collections as collection_commands,
)
from ..db.queries import (
    auth as auth_queries,
    collections as collection_queries,
)
from ..exceptions import PottoException
from ..schemas.auth import PottoScope, PottoUser
from ..schemas.base import (
    CollectionProvider,
    CollectionProviderConfiguration,
    CollectionType,
)
from ..schemas.auth import UserUpdate
from ..schemas.collections import (
    CollectionCreate,
    CollectionUpdate,
)

logger = logging.getLogger(__name__)


async def collect_all_collections(
        session: AsyncSession,
        user: PottoUser | None,
        authorization_backend: AuthorizationBackendProtocol,
        collection_type_filter: list[CollectionType] | None = None,
) -> list[Collection]:
    """List all collections that the user has access to."""
    accessible_ids = await authorization_backend.get_accessible_collection_identifiers(user)
    if accessible_ids is None:
        return await collection_queries.collect_all_collections(
            session,
            collection_type_filter=collection_type_filter,
            is_public_filter=None,
        )
    return await collection_queries.collect_all_collections(
        session,
        collection_type_filter=collection_type_filter,
        user_id=user.id if user is not None else None,
        accessible_identifiers=accessible_ids,
    )


async def paginated_list_collections(
        session: AsyncSession,
        user: PottoUser | None,
        authorization_backend: AuthorizationBackendProtocol,
        *,
        page: int = 1,
        page_size: int = 20,
        include_total: bool = False,
        identifier_filter: str | None = None,
        collection_type_filter: list[CollectionType] | None = None,
        spatial_intersect: shapely.Polygon | None = None,
) -> tuple[list[Collection], int | None]:
    """Produce a paginated list of all collections that the user has access to."""
    accessible_ids = await authorization_backend.get_accessible_collection_identifiers(user)
    if accessible_ids is None:
        return await collection_queries.paginated_list_collections(
            session,
            page=page,
            page_size=page_size,
            include_total=include_total,
            identifier_filter=identifier_filter,
            is_public_filter=None,
            collection_type_filter=collection_type_filter,
            spatial_intersect=spatial_intersect,
        )
    return await collection_queries.paginated_list_collections(
        session,
        page=page,
        page_size=page_size,
        include_total=include_total,
        identifier_filter=identifier_filter,
        user_id=user.id if user is not None else None,
        accessible_identifiers=accessible_ids,
        collection_type_filter=collection_type_filter,
        spatial_intersect=spatial_intersect,
    )


async def get_collection(
        session: AsyncSession,
        user: PottoUser | None,
        authorization_backend: AuthorizationBackendProtocol,
        collection_id: int,
) -> Collection | None:
    collection = await collection_queries.get_collection(session, collection_id)
    if collection is None:
        return None
    if not await authorization_backend.can_view_collection(user, collection):
        return None
    return collection


async def get_collection_by_resource_identifier(
        session: AsyncSession,
        user: PottoUser | None,
        authorization_backend: AuthorizationBackendProtocol,
        identifier: str,
) -> Collection | None:
    collection = await collection_queries.get_collection_by_resource_identifier(session, identifier)
    if collection is None:
        return None
    if not await authorization_backend.can_view_collection(user, collection):
        return None
    return collection


async def create_collection(
        session: AsyncSession,
        to_create: CollectionCreate,
) -> Collection:
    return await collection_commands.create_collection(session, to_create)


async def delete_collection(
        session: AsyncSession,
        user: PottoUser,
        authorization_backend: AuthorizationBackendProtocol,
        collection_id: int,
) -> None:
    collection = await collection_queries.get_collection(session, collection_id)
    if collection is None:
        raise PottoException(f"Collection with id {collection_id} does not exist.")
    if not await authorization_backend.can_edit_collection(user, collection):
        raise PottoException(f"User does not have permission to delete collection {collection_id}.")
    return await collection_commands.delete_collection(session, collection_id)


async def grant_collection_access(
        session: AsyncSession,
        granting_user: PottoUser,
        authorization_backend: AuthorizationBackendProtocol,
        target_user_id: str,
        collection: Collection,
        role: str,
) -> None:
    if not await authorization_backend.can_edit_collection(granting_user, collection):
        raise PottoException("User does not have permission to grant access to this collection.")
    target_user = await auth_queries.get_user(session, target_user_id)
    if target_user is None:
        raise PottoException(f"User with id {target_user_id!r} does not exist.")
    editor_scope = PottoScope.collection_editor(collection.resource_identifier)
    viewer_scope = PottoScope.collection_viewer(collection.resource_identifier)
    new_scopes = [s for s in target_user.scopes if s not in (editor_scope, viewer_scope)]
    if role == "editor":
        new_scopes.append(editor_scope)
    else:
        new_scopes.append(viewer_scope)
    await auth_commands.update_user(session, target_user, UserUpdate(scopes=new_scopes))


async def revoke_collection_access(
        session: AsyncSession,
        revoking_user: PottoUser,
        authorization_backend: AuthorizationBackendProtocol,
        target_user_id: str,
        collection: Collection,
) -> None:
    if not await authorization_backend.can_edit_collection(revoking_user, collection):
        raise PottoException("User does not have permission to revoke access to this collection.")
    target_user = await auth_queries.get_user(session, target_user_id)
    if target_user is None:
        raise PottoException(f"User with id {target_user_id!r} does not exist.")
    editor_scope = PottoScope.collection_editor(collection.resource_identifier)
    viewer_scope = PottoScope.collection_viewer(collection.resource_identifier)
    new_scopes = [s for s in target_user.scopes if s not in (editor_scope, viewer_scope)]
    await auth_commands.update_user(session, target_user, UserUpdate(scopes=new_scopes))


async def import_pygeoapi_collection(
        session: AsyncSession,
        user: User,
        authorization_backend: AuthorizationBackendProtocol,
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
        if not await authorization_backend.can_edit_collection(user, existing_db_collection):
            raise PottoException(f"User does not have permission to overwrite collection {identifier!r}.")
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
