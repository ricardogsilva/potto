"""Permission-checked business logic backing ``PostgisManager``.

The functions defined in this module always return instances of potto's public,
storage-agnostic schemas (``potto.schemas.*``), never this package's private ORM
models.
"""

import copy
import datetime as dt
import logging
import re
from typing import cast, TYPE_CHECKING

import bcrypt
import shapely
from sqlalchemy.exc import DatabaseError
from sqlmodel.ext.asyncio.session import AsyncSession

from ... import util
from ...authz.protocols import AuthorizationBackendProtocol
from ...constants import (
    CollectionType,
    CRS_84,
    CRS_84h,
)
from ...exceptions import (
    PottoCannotChangeCollectionOwnerException,
    PottoCannotCreateCollectionException,
    PottoCannotCreateUserException,
    PottoCannotDeleteCollectionException,
    PottoCannotEditCollectionException,
    PottoCannotEditServerMetadataException,
    PottoCannotModifyCollectionAccessException,
    PottoCannotSetAdminScopeException,
    PottoCannotSetScopesException,
    PottoCollectionNotFoundException,
    PottoException,
    PottoNotFoundException,
)
from ...providers.features.registry import get_feature_provider
from ...schemas.auth import (
    PottoScope,
    PottoUser,
    UserCreate,
    UserCreateFromOidc,
    UserUpdate,
)
from ...schemas.base import PottoProvider
from ...schemas.collections import (
    Collection as CollectionSchema,
    CollectionCreate,
    CollectionUpdate,
)
from ...schemas.metadata import (
    ServerMetadata,
    ServerMetadataCreate,
    ServerMetadataUpdate,
)
from .db.commands import (
    auth as auth_commands,
    collections as collection_commands,
    metadata as metadata_commands,
)
from .db.models import Collection
from .db.queries import (
    auth as auth_queries,
    collections as collection_queries,
    get_metadata,
)

if TYPE_CHECKING:
    from ...config import PottoSettings

logger = logging.getLogger(__name__)

_EDITOR_SCOPE_RE = re.compile(r"^collection-(.+):editor$")


# --- collections ------------------------------------------------------------


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
) -> tuple[list[CollectionSchema], int | None]:
    """Produce a paginated list of all collections that the user has access to."""
    if user is None:
        (
            public_collections,
            count,
        ) = await collection_queries.paginated_list_public_collections(
            session,
            page=page,
            page_size=page_size,
            include_total=include_total,
            identifier_filter=identifier_filter,
            collection_type_filter=collection_type_filter,
            spatial_intersect=spatial_intersect,
        )
        return [col.to_potto() for col in public_collections], count
    accessible_ids = await authorization_backend.get_accessible_collection_identifiers(
        user
    )
    (
        accessible_collections,
        count,
    ) = await collection_queries.paginated_list_user_collections(
        session,
        page=page,
        page_size=page_size,
        include_total=include_total,
        identifier_filter=identifier_filter,
        user_id=user.id,
        accessible_identifiers=accessible_ids,
        collection_type_filter=collection_type_filter,
        spatial_intersect=spatial_intersect,
    )
    return [
        accessible_col.to_potto() for accessible_col in accessible_collections
    ], count


async def get_collection_by_resource_identifier(
    session: AsyncSession,
    user: PottoUser | None,
    authorization_backend: AuthorizationBackendProtocol,
    identifier: str,
) -> CollectionSchema | None:
    resource = await collection_queries.get_collection_by_resource_identifier(
        session, identifier
    )
    if resource is None:
        return None
    collection = resource.to_potto()
    if not await authorization_backend.can_view_collection(user, collection):
        return None
    return collection


async def _enrich_from_provider(
    session: AsyncSession,
    collection: Collection,
    potto_settings: "PottoSettings",
) -> Collection:
    try:
        provider = await get_feature_provider(collection.to_potto(), potto_settings)
    except Exception:
        logger.warning(
            "Failed to instantiate feature provider for collection enrichment"
        )
        return collection
    if provider is None:
        return collection

    update_kwargs: dict = {}
    try:
        if collection.storage_crs is None:
            if (storage_crs := await provider.get_storage_crs()) is not None:
                update_kwargs["storage_crs"] = storage_crs.crs
                if storage_crs.coordinate_epoch is not None:
                    update_kwargs["storage_crs_coordinate_epoch"] = (
                        storage_crs.coordinate_epoch
                    )

        if collection.spatial_extent is None:
            if (spatial_extent := await provider.get_spatial_extent()) is not None:
                bbox = spatial_extent.bbox[0]
                update_kwargs["spatial_extent"] = shapely.box(
                    bbox[0], bbox[1], bbox[2], bbox[3]
                )
                update_kwargs["spatial_extent_crs"] = spatial_extent.crs

        if (
            collection.temporal_extent_begin is None
            and collection.temporal_extent_end is None
        ):
            if (temporal_extent := await provider.get_temporal_extent()) is not None:
                if temporal_extent.interval:
                    begin_str, end_str = temporal_extent.interval[0]
                    if begin_str is not None:
                        update_kwargs["temporal_extent_begin"] = (
                            dt.datetime.fromisoformat(begin_str)
                        )
                    if end_str is not None:
                        update_kwargs["temporal_extent_end"] = (
                            dt.datetime.fromisoformat(end_str)
                        )

        if collection.additional_extents is None:
            if (
                additional_extents := await provider.get_additional_extents()
            ) is not None:
                update_kwargs["additional_extents"] = additional_extents
    except Exception:
        logger.exception("Failed to enrich collection from provider")
        return collection

    if not update_kwargs:
        return collection
    return await collection_commands.update_collection(
        session, collection, CollectionUpdate(**update_kwargs)
    )


async def create_collection(
    session: AsyncSession,
    user: PottoUser | None,
    authorization_backend: AuthorizationBackendProtocol,
    to_create: CollectionCreate,
    potto_settings: "PottoSettings",
) -> CollectionSchema:
    if not await authorization_backend.can_create_collection(user):
        raise PottoCannotCreateCollectionException(
            "User does not have permission to create a collection."
        )
    try:
        created = await collection_commands.create_collection(session, to_create)
    except DatabaseError as err:
        await session.rollback()
        raise PottoCannotCreateCollectionException(str(err)) from err
    created = await _enrich_from_provider(session, created, potto_settings)
    if created.storage_crs is None:
        created = await collection_commands.update_collection(
            session, created, CollectionUpdate(storage_crs=CRS_84)
        )
    return created.to_potto()


async def update_collection(
    session: AsyncSession,
    user: PottoUser | None,
    authorization_backend: AuthorizationBackendProtocol,
    collection: CollectionSchema,
    to_update: CollectionUpdate,
) -> CollectionSchema:
    if not await authorization_backend.can_edit_collection(user, collection):
        raise PottoCannotEditCollectionException(
            f"User does not have permission to edit collection "
            f"{collection.identifier!r}."
        )
    if to_update.owner_id is not None and to_update.owner_id != collection.owner.id:
        if not await authorization_backend.can_change_collection_owner(
            user, collection
        ):
            raise PottoCannotChangeCollectionOwnerException(
                f"User does not have permission to change the owner of collection "
                f"{collection.identifier!r}."
            )
    try:
        db_collection = await collection_queries.get_collection_by_resource_identifier(
            session, collection.identifier
        )
        if db_collection is None:
            raise PottoCollectionNotFoundException(
                f"collection {collection.identifier!r} not found"
            )
        updated = await collection_commands.update_collection(
            session, db_collection, to_update
        )
        return updated.to_potto()
    except DatabaseError as err:
        raise PottoCannotEditCollectionException(str(err)) from err


async def delete_collection(
    session: AsyncSession,
    user: PottoUser,
    authorization_backend: AuthorizationBackendProtocol,
    identifier: str,
) -> None:
    db_collection = await collection_queries.get_collection_by_resource_identifier(
        session, identifier
    )
    if db_collection is None:
        raise PottoException(f"Collection {identifier!r} does not exist.")
    if not await authorization_backend.can_edit_collection(
        user, db_collection.to_potto()
    ):
        raise PottoCannotDeleteCollectionException(
            f"User does not have permission to delete collection {identifier!r}."
        )
    try:
        return await collection_commands.delete_collection(
            session, cast(int, db_collection.id)
        )
    except DatabaseError as err:
        raise PottoCannotDeleteCollectionException(str(err)) from err


async def grant_collection_access(
    session: AsyncSession,
    granting_user: PottoUser,
    authorization_backend: AuthorizationBackendProtocol,
    target_user_id: str,
    collection: CollectionSchema,
    role: str,
) -> None:
    if not await authorization_backend.can_edit_collection(granting_user, collection):
        raise PottoException(
            "User does not have permission to grant access to this collection."
        )
    target_user = await auth_queries.get_user(session, target_user_id)
    if target_user is None:
        raise PottoException(f"User with id {target_user_id!r} does not exist.")
    editor_scope = PottoScope.collection_editor(collection.identifier)
    viewer_scope = PottoScope.collection_viewer(collection.identifier)
    new_scopes = [
        s for s in target_user.scopes if s not in (editor_scope, viewer_scope)
    ]
    if role == "editor":
        new_scopes.append(editor_scope)
    else:
        new_scopes.append(viewer_scope)
    try:
        await auth_commands.update_user(
            session, target_user, UserUpdate(scopes=new_scopes)
        )
    except DatabaseError as err:
        raise PottoCannotModifyCollectionAccessException(str(err)) from err


async def revoke_collection_access(
    session: AsyncSession,
    revoking_user: PottoUser,
    authorization_backend: AuthorizationBackendProtocol,
    target_user_id: str,
    collection: CollectionSchema,
) -> None:
    if not await authorization_backend.can_edit_collection(revoking_user, collection):
        raise PottoException(
            "User does not have permission to revoke access to this collection."
        )
    target_user = await auth_queries.get_user(session, target_user_id)
    if target_user is None:
        raise PottoException(f"User with id {target_user_id!r} does not exist.")
    editor_scope = PottoScope.collection_editor(collection.identifier)
    viewer_scope = PottoScope.collection_viewer(collection.identifier)
    new_scopes = [
        s for s in target_user.scopes if s not in (editor_scope, viewer_scope)
    ]
    try:
        await auth_commands.update_user(
            session, target_user, UserUpdate(scopes=new_scopes)
        )
    except DatabaseError as err:
        raise PottoCannotModifyCollectionAccessException(str(err)) from err


def _get_crs_info(
    pygeoapi_collection: dict,
) -> tuple[list[str], str | None, str | None]:
    supported_crs = {CRS_84}
    storage_crs = None
    storage_crs_coordinate_epoch = None
    for provider_conf in pygeoapi_collection.get("providers", []):
        if (advertised_crs_list := provider_conf.get("crs")) is not None:
            supported_crs.update(advertised_crs_list)
        if (provider_storage_crs := provider_conf.get("storage_crs")) is not None:
            storage_crs = provider_storage_crs
        if (
            provider_storage_crs_coordinate_epoch := provider_conf.get(
                "storage_crs_coordinate_epoch"
            )
        ) is not None:
            storage_crs_coordinate_epoch = provider_storage_crs_coordinate_epoch
        if all((storage_crs, supported_crs, storage_crs_coordinate_epoch)):
            break
    return list(supported_crs), storage_crs, storage_crs_coordinate_epoch


async def import_pygeoapi_collection(
    session: AsyncSession,
    user: PottoUser,
    authorization_backend: AuthorizationBackendProtocol,
    identifier: str,
    pygeoapi_collection: dict,
    potto_settings: "PottoSettings",
    *,
    overwrite: bool = False,
) -> CollectionSchema:
    existing_db_collection = (
        await collection_queries.get_collection_by_resource_identifier(
            session, identifier
        )
    )
    if existing_db_collection and not overwrite:
        raise PottoException(f"Collection {identifier!r} already exists!")
    resource_spatial_extents = pygeoapi_collection.get("extents", {}).get("spatial", {})
    spatial_extent = None
    spatial_extent_crs = None
    try:
        if (raw_bbox := resource_spatial_extents.get("bbox")) is not None:
            spatial_extent = shapely.box(*raw_bbox)
            spatial_extent_crs = resource_spatial_extents.get(
                "crs", CRS_84h if spatial_extent.has_z else CRS_84
            )
            # TODO: convert the bbox to either CRS84 or CRS84h, if given something else
    except TypeError:
        logger.exception(
            f"Could not extract bbox from collection {identifier!r}, setting "
            f"spatial_extent to None"
        )
    supported_crs = None
    storage_crs = None
    storage_crs_coordinate_epoch = None
    if spatial_extent is not None:
        supported_crs, storage_crs, storage_crs_coordinate_epoch = _get_crs_info(
            pygeoapi_collection
        )
    providers = {}
    for prov in pygeoapi_collection.get("providers", []):
        modifiable_prov = copy.deepcopy(prov)
        if (type_ := modifiable_prov.pop("type")) in providers.keys():
            continue
        providers[type_] = PottoProvider(
            provider_name="pygeoapi",
            config={
                "python_callable": modifiable_prov.pop("name"),
                "data": modifiable_prov.pop("data"),
                "options": modifiable_prov,
            },
        )

    collection_type = util.get_collection_type(pygeoapi_collection)
    if existing_db_collection and overwrite:
        if not await authorization_backend.can_edit_collection(
            user, existing_db_collection.to_potto()
        ):
            raise PottoException(
                f"User does not have permission to overwrite collection {identifier!r}."
            )
        logger.debug(f"Updating existing collection {identifier!r}...")
        to_update = CollectionUpdate(
            collection_type=collection_type,
            title=pygeoapi_collection.get("title", ""),
            description=pygeoapi_collection.get("description"),
            keywords=pygeoapi_collection.get("keywords"),
            spatial_extent=spatial_extent,
            spatial_extent_crs=spatial_extent_crs,
            crs=supported_crs,
            storage_crs=storage_crs,
            storage_crs_coordinate_epoch=storage_crs_coordinate_epoch,
            temporal_extent_begin=pygeoapi_collection.get("extents", {})
            .get("temporal", {})
            .get("begin"),
            temporal_extent_end=pygeoapi_collection.get("extents", {})
            .get("temporal", {})
            .get("end"),
            additional_links=pygeoapi_collection.get("links"),
            providers=providers,
        )
        imported = await collection_commands.update_collection(
            session, existing_db_collection, to_update
        )
        return imported.to_potto()
    else:
        to_create = CollectionCreate(
            resource_identifier=identifier,
            owner_id=user.id,
            collection_type=collection_type,
            title=pygeoapi_collection.get("title", ""),
            description=pygeoapi_collection.get("description"),
            keywords=pygeoapi_collection.get("keywords"),
            spatial_extent=spatial_extent,
            spatial_extent_crs=spatial_extent_crs,
            crs=supported_crs,
            storage_crs=storage_crs,
            storage_crs_coordinate_epoch=storage_crs_coordinate_epoch,
            temporal_extent_begin=pygeoapi_collection.get("extents", {})
            .get("temporal", {})
            .get("begin"),
            temporal_extent_end=pygeoapi_collection.get("extents", {})
            .get("temporal", {})
            .get("end"),
            additional_links=pygeoapi_collection.get("links"),
            providers=providers,
        )
        return await create_collection(
            session, user, authorization_backend, to_create, potto_settings
        )


# --- server metadata ---------------------------------------------------------


async def get_server_metadata(session: AsyncSession) -> ServerMetadata:
    """Return pre-existing server metadata, creating a default record if none exists."""
    if existing := await get_metadata(session):
        return existing.to_potto()
    created = await metadata_commands.create_metadata(
        session, ServerMetadataCreate(title="Default title")
    )
    return created.to_potto()


async def update_server_metadata(
    session: AsyncSession,
    user: PottoUser | None,
    authorization_backend: AuthorizationBackendProtocol,
    to_update: ServerMetadataUpdate,
) -> ServerMetadata:
    if not await authorization_backend.can_edit_server_metadata(user):
        raise PottoCannotEditServerMetadataException(
            "User does not have permission to edit server metadata."
        )
    db_metadata = await get_metadata(session)
    if db_metadata is None:
        db_metadata = await metadata_commands.create_metadata(
            session, ServerMetadataCreate(title="Default title")
        )
    updated = await metadata_commands.update_metadata(session, db_metadata, to_update)
    return updated.to_potto()


# --- user accounts ------------------------------------------------------------


async def create_user(
    session: AsyncSession,
    requesting_user: PottoUser | None,
    authorization_backend: AuthorizationBackendProtocol,
    to_create: UserCreate,
) -> PottoUser:
    if not await authorization_backend.can_create_user(requesting_user):
        raise PottoCannotCreateUserException(
            "User does not have permission to create new users."
        )
    if to_create.scopes:
        await _check_scope_assignment(
            session, requesting_user, authorization_backend, to_create.scopes
        )
    created = await auth_commands.create_user(session, to_create)
    return created.to_potto()


async def update_user(
    session: AsyncSession,
    requesting_user: PottoUser | None,
    authorization_backend: AuthorizationBackendProtocol,
    user_id: str,
    to_update: UserUpdate,
) -> PottoUser:
    db_user = await auth_queries.get_user(session, user_id)
    if db_user is None:
        raise PottoNotFoundException(f"User {user_id!r} does not exist.")
    if to_update.scopes is not None:
        await _check_scope_assignment(
            session, requesting_user, authorization_backend, to_update.scopes
        )
    updated = await auth_commands.update_user(session, db_user, to_update)
    return updated.to_potto()


async def _check_scope_assignment(
    session: AsyncSession,
    requesting_user: PottoUser | None,
    authorization_backend: AuthorizationBackendProtocol,
    new_scopes: list[str],
) -> None:
    if PottoScope.ADMIN.value in new_scopes:
        if not await authorization_backend.can_assign_admin_scope(requesting_user):
            raise PottoCannotSetAdminScopeException(
                "User does not have permission to assign the admin scope."
            )
    editable_identifiers = await _get_editable_collection_identifiers(
        session, requesting_user
    )
    if not await authorization_backend.can_set_user_scopes(
        requesting_user, new_scopes, editable_identifiers
    ):
        raise PottoCannotSetScopesException(
            "User does not have permission to set these scopes."
        )


async def _get_editable_collection_identifiers(
    session: AsyncSession,
    user: PottoUser | None,
) -> list[str]:
    if user is None:
        return []
    owned = await collection_queries.get_owned_collection_identifiers(session, user.id)
    from_scopes = [
        m.group(1) for scope in user.scopes if (m := _EDITOR_SCOPE_RE.match(scope))
    ]
    return list({*owned, *from_scopes})


async def delete_user(
    session: AsyncSession,
    requesting_user: PottoUser | None,
    user_id: str,
) -> None:
    # TODO: check user permissions
    return await auth_commands.delete_user(session, user_id)


async def paginated_list_users(
    session: AsyncSession,
    *,
    admin_filter: bool = False,
    page: int = 1,
    page_size: int = 20,
    include_total: bool = False,
) -> tuple[list[PottoUser], int | None]:
    # TODO: check user permissions
    users, count = await auth_queries.paginated_list_users(
        session,
        page=page,
        page_size=page_size,
        include_total=include_total,
        admin_filter=admin_filter,
    )
    return [u.to_potto() for u in users], count


async def get_user(
    session: AsyncSession,
    user_id: str,
) -> PottoUser | None:
    # TODO: check user permissions
    db_user = await auth_queries.get_user(session, user_id)
    return db_user.to_potto() if db_user is not None else None


async def get_user_by_username(
    session: AsyncSession,
    username: str,
) -> PottoUser | None:
    db_user = await auth_queries.get_user_by_username(session, username)
    return db_user.to_potto() if db_user is not None else None


async def provision_oidc_user(
    session: AsyncSession,
    to_create: UserCreateFromOidc,
) -> PottoUser:
    created = await auth_commands.provision_oidc_user(session, to_create)
    return created.to_potto()


async def authenticate(
    session: AsyncSession,
    username: str,
    password: str,
) -> PottoUser | None:
    """Verify a local username/password pair, returning None on any failure."""
    db_user = await auth_queries.get_user_by_username(session, username)
    if db_user is None:
        logger.debug(f"Login failed: user {username!r} not found")
        return None
    if not db_user.is_active:
        logger.warning(f"Login failed: user {username!r} is inactive")
        return None
    if db_user.hashed_password is None:
        logger.warning(f"Login failed: user {username!r} has no local password")
        return None
    if not bcrypt.checkpw(password.encode(), db_user.hashed_password.encode()):
        logger.debug(f"Login failed: wrong password for user {username!r}")
        return None
    return db_user.to_potto()


async def list_resource_editors(
    session: AsyncSession,
    resource_type: str,
    resource_identifier: str,
) -> list[PottoUser]:
    if resource_type != "collection":
        raise NotImplementedError(
            f"Resource type {resource_type!r} is not supported yet."
        )
    editors = await collection_queries.get_collection_editors(
        session, resource_identifier
    )
    return [e.to_potto() for e in editors]


async def list_resource_viewers(
    session: AsyncSession,
    resource_type: str,
    resource_identifier: str,
) -> list[PottoUser]:
    if resource_type != "collection":
        raise NotImplementedError(
            f"Resource type {resource_type!r} is not supported yet."
        )
    viewers = await collection_queries.get_collection_viewers(
        session, resource_identifier
    )
    return [v.to_potto() for v in viewers]
