import logging
from typing import Annotated

import babel
from fastapi import (
    APIRouter,
    Query,
    Request,
)

from ....schemas.base import (
    ItemFilter,
    FeatureFilter,
)
from ....schemas.web.items import (
    GeoJsonItem,
    GeoJsonItemCollection,
)
from ..dependencies import (
    LocaleDependency,
    PottoDependency,
    UserDependency,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/collections/{collection_id}/items",
    name="collection-item-list",
    tags=["items"],
)
async def list_collection_items(
        request: Request,
        collection_id: str,
        filter_: Annotated[ItemFilter, Query()],
        potto: PottoDependency,
        user: UserDependency,
        locale: LocaleDependency,
) -> GeoJsonItemCollection:
    result = await potto.api_list_collection_items(
        collection_id,
        user=user,
        locale=locale,
        filter_=FeatureFilter(**filter_.model_dump()),
    )
    return GeoJsonItemCollection.from_potto(result, request.url_for)


@router.get(
    "/collections/{collection_id}/items/{item_id}",
    name="collection-item-get",
    tags=["items"],
)
async def get_item_details(
        request: Request,
        potto: PottoDependency,
        user: UserDependency,
        collection_id: str,
        item_id: str,
) -> GeoJsonItem:
    current_locale = babel.Locale.parse(request.state.language)
    result = await potto.api_get_collection_item(
        user,
        collection_id=collection_id,
        item_id=item_id,
        locale=current_locale,
    )
    return GeoJsonItem.from_potto(result.feature, result.resource, request.url_for)
