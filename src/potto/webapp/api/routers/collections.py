import logging

import babel
from fastapi import (
    APIRouter,
    HTTPException,
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
from ....schemas.web import GeoJsonItem, GeoJsonItemCollection
from ....schemas.web.items import ItemFilter
from ..dependencies import (
    PottoDependency,
    SettingsDependency,
)

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.get(
    "/collections",
    name="list-collections",
)
async def list_collections(request: Request, settings: SettingsDependency) -> JsonCollectionList:
    async with settings.get_db_session_maker()() as session:
        db_collections, total = await collection_operations.paginated_list_collections(
            session,
            page=1,
            page_size=20,
            include_total=True
        )
    return JsonCollectionList.from_db_items(db_collections, request.url_for)


@router.get(
    "/collections/{collection_id}",
    name="get-collection",
    response_model=JsonCollection,
)
async def get_collection_details(
        collection_id: str,
        request: Request,
        settings: SettingsDependency,
) -> JsonCollection:
    async with settings.get_db_session_maker()() as session:
        db_collection = await collection_operations.get_collection_by_resource_identifier(
            session, collection_id)
        if not db_collection:
            raise HTTPException(status_code=404, detail="Collection not found")
    return JsonCollection.from_db_item(db_collection, request.url_for)
