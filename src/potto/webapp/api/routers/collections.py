import logging

from fastapi import (
    APIRouter,
    Request,
)

from ....operations import collections as collection_operations
from ....schemas import (
    collections as collections_schemas,
)
from ....schemas.web.collections import (
    JsonCollectionList,
    JsonCollection,
)
from ..dependencies import (
    LocaleDependency,
    PottoDependency,
    SettingsDependency,
    UserDependency,
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/collections",
    name="list-collections",
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
    name="get-collection",
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
):
    async with settings.get_db_session_maker()() as session:
        db_collection = await collection_operations.create_collection(session, to_create)
    return JsonCollection.from_db_item(db_collection, request.url_for)


@router.delete(
    "/collections/{collection_id}",
    name="delete-collection",
)
async def delete_collection(
        collection_id: str,
        settings: SettingsDependency,
):
    async with settings.get_db_session_maker()() as session:
        await collection_operations.delete_collection(session, collection_id)


