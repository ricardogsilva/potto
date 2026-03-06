import logging
from typing import Annotated

import babel
from fastapi import (
    APIRouter,
    Query,
    Request,
)

from .... import constants
from ....operations import collections as collection_operations
from ....schemas import (
    collections as collections_schemas,
)
from ....schemas.web.collections import (
    GeoJsonItem,
    GeoJsonItemCollection,
    ItemFilter,
    JsonCollectionList,
    JsonCollection,
)
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
    return JsonCollectionList.from_db_instances()
    current_locale = babel.Locale.parse(request.state.language)
    result = await potto.api_list_collections(
        locale=current_locale,
        output_format="json",
    )
    return JsonCollectionList.from_potto(result, request.url_for)


@router.get(
    "/collections/{collection_id}",
    name="get-collection",
    response_model=JsonCollection,
)
async def get_collection_details(
        request: Request,
        potto: PottoDependency,
        collection_id: str,
) -> JsonCollection:
    current_locale = babel.Locale.parse(request.state.language)
    result = await potto.api_get_collection(
        collection_id=collection_id,
        locale=current_locale,
        output_format=constants.PYGEOAPI_F_JSON,
    )
    return JsonCollection(
        **result.collection.model_dump(by_alias=True),
        links=[]
    )


@router.get(
    "/collections/{collection_id}/items",
    name="list-collection-items"
)
async def list_collection_items(
        request: Request,
        potto: PottoDependency,
        collection_id: str,
        filter_: Annotated[ItemFilter, Query()],
) -> GeoJsonItemCollection:
    current_locale = babel.Locale.parse(request.state.language)
    result = await potto.api_list_collection_items(
        collection_id,
        locale=current_locale,
        filter_=collections_schemas.FeatureFilter(**filter_.model_dump()),
    )
    return GeoJsonItemCollection.from_potto(result, request.url_for)


@router.get(
    "/collections/{collection_id}/items/{item_id}",
    name="get-item"
)
async def get_item_details(
        request: Request,
        potto: PottoDependency,
        collection_id: str,
        item_id: str,
) -> GeoJsonItem:
    current_locale = babel.Locale.parse(request.state.language)
    result = await potto.api_get_item(
        collection_id=collection_id,
        item_id=item_id,
        locale=current_locale,
    )
    return GeoJsonItem.from_potto(result.feature, result.resource, request.url_for)
