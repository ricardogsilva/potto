import logging
from typing import Annotated

import babel
from fastapi import (
    APIRouter,
    Query,
    Request,
)

from .... import constants
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
from ....wrapper import Potto

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/collections",
    name="list-collections"
)
async def list_collections(request: Request) -> JsonCollectionList:
    current_locale = babel.Locale.parse(request.state.language)
    potto: Potto = request.state.potto
    result = await potto.api_list_collections(
        locale=current_locale,
        output_format=constants.PYGEOAPI_F_JSON,
    )
    return JsonCollectionList(
        collections=[c.model_dump(by_alias=True) for c in result.collections],
        links=[],
    )


@router.get(
    "/collections/{collection_id}",
    name="get-collection"
)
async def get_collection_details(
        request: Request,
        collection_id: str
) -> JsonCollection:
    current_locale = babel.Locale.parse(request.state.language)
    potto: Potto = request.state.potto
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
        collection_id: str,
        filter_: Annotated[ItemFilter, Query()]
) -> GeoJsonItemCollection:
    current_locale = babel.Locale.parse(request.state.language)
    potto: Potto = request.state.potto
    result = await potto.api_list_collection_items(
        collection_id=collection_id,
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
        collection_id: str,
        item_id: str,
) -> GeoJsonItem:
    current_locale = babel.Locale.parse(request.state.language)
    potto: Potto = request.state.potto
    result = await potto.api_get_item(
        collection_id=collection_id,
        item_id=item_id,
        locale=current_locale,
    )
    return GeoJsonItem.from_potto(result.feature, result.resource, request.url_for)
