import logging

from fastapi import (
    APIRouter,
    Request,
)

from ....exceptions import PottoException
from ....operations import collections as collection_operations
from ....schemas import (
    collections as collections_schemas,
)
from ....schemas.web.collections import (
    JsonCollectionList,
    JsonCollection,
)
from ..dependencies import (
    AuthorizationBackendDependency,
    LocaleDependency,
    PottoDependency,
    SettingsDependency,
    UserDependency,
)


logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/collections",
    name="collection-list",
    response_model_exclude_none=True,
    response_model=JsonCollectionList
)
async def list_collections(
        request: Request,
        potto: PottoDependency,
        user: UserDependency,
        locale: LocaleDependency,
) -> JsonCollectionList:
    potto_collections = await potto.api_list_collections(
        user=user, locale=locale)
    return JsonCollectionList.from_potto(potto_collections, request.url_for)


@router.get(
    "/collections/{collection_id}",
    name="collection-get",
    response_model=JsonCollection,
)
async def get_collection_details(
        request: Request,
        collection_id: str,
        potto: PottoDependency,
        user: UserDependency,
        locale: LocaleDependency,
) -> JsonCollection:
    potto_collection = await potto.api_get_collection(
        collection_id, user=user, locale=locale)
    return JsonCollection.from_potto(potto_collection, request.url_for)


@router.post(
    "/collections",
    name="create-collection",
    response_model=JsonCollection
)
async def create_collection(
        request: Request,
        to_create: collections_schemas.CollectionCreate,
        settings: SettingsDependency,
        user: UserDependency,
        authorization_backend: AuthorizationBackendDependency,
):
    async with settings.get_db_session_maker()() as session:
        db_collection = await collection_operations.create_collection(
            session, user, authorization_backend, to_create
        )
    return JsonCollection.from_db_item(db_collection, request.url_for)


@router.delete(
    "/collections/{collection_id}",
    name="delete-collection",
)
async def delete_collection(
        collection_id: str,
        user: UserDependency,
        authorization_backend: AuthorizationBackendDependency,
        settings: SettingsDependency,
):
    async with settings.get_db_session_maker()() as session:
        await collection_operations.delete_collection(
            session, user, authorization_backend, int(collection_id)
        )


@router.put(
    "/collections/{collection_id}/access/{user_id}",
    name="grant-collection-access",
    status_code=204,
)
async def grant_collection_access(
        collection_id: str,
        user_id: str,
        body: collections_schemas.CollectionAccessGrant,
        user: UserDependency,
        authorization_backend: AuthorizationBackendDependency,
        settings: SettingsDependency,
):
    async with settings.get_db_session_maker()() as session:
        collection = await collection_operations.get_collection_by_resource_identifier(
            session, user, authorization_backend, collection_id
        )
        if collection is None:
            raise PottoException(f"Collection {collection_id!r} not found.")
        await collection_operations.grant_collection_access(
            session, user, authorization_backend, user_id, collection, body.role
        )


@router.delete(
    "/collections/{collection_id}/access/{user_id}",
    name="revoke-collection-access",
    status_code=204,
)
async def revoke_collection_access(
        collection_id: str,
        user_id: str,
        user: UserDependency,
        authorization_backend: AuthorizationBackendDependency,
        settings: SettingsDependency,
):
    async with settings.get_db_session_maker()() as session:
        collection = await collection_operations.get_collection_by_resource_identifier(
            session, user, authorization_backend, collection_id
        )
        if collection is None:
            raise PottoException(f"Collection {collection_id!r} not found.")
        await collection_operations.revoke_collection_access(
            session, user, authorization_backend, user_id, collection
        )
