import copy
import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.responses import JSONResponse

from ....constants import MEDIA_TYPE_JSON_SCHEMA
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
    PaginationLimitDependency,
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
        limit: PaginationLimitDependency
) -> JsonCollectionList:
    logger.debug(f"{locals()=}")
    potto_collections = await potto.api_list_collections(
        user=user, locale=locale, page_size=limit)
    return JsonCollectionList.from_potto(potto_collections, request.url_for)


@router.head(
    "/collections/{collection_id}",
    name="collection-head",
    response_model=None,
)
async def head_collection_details(
        request: Request,
        collection_id: str,
        potto: PottoDependency,
        user: UserDependency,
        locale: LocaleDependency,
) -> Response:
    if (
            potto_collection := await potto.api_get_collection(
                collection_id, user=user, locale=locale)
    ) is None:
        raise HTTPException(status_code=404, detail="Collection not found.")
    links = JsonCollection.get_links(
        potto_collection.identifier,
        request.url_for,
        additional_links=potto_collection.additional_links
    )
    return Response(
        headers={
            "Link": ",".join((li.serialize_as_http_header() for li in links))
        }
    )


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
):
    if (
            potto_collection := await potto.api_get_collection(
                collection_id, user=user, locale=locale)
    ) is None:
        raise HTTPException(status_code=404, detail="Collection not found.")
    result = JsonCollection.from_potto(potto_collection, request.url_for)
    return JSONResponse(
        result.model_dump_json(exclude_none=True),
        headers={
            "Link": ",".join((li.serialize_as_http_header() for li in result.links))
        }
    )


@router.get(
    "/collections/{collection_id}/queryables",
    name="collection-get-queryables",
)
async def get_collection_queryables(
        request: Request,
        collection_id: str,
        potto: PottoDependency,
        user: UserDependency,
        locale: LocaleDependency,
) -> JSONResponse:
    potto_collection = await potto.api_get_collection(
        collection_id, user=user, locale=locale, include_queryables=True)
    if potto_collection is None:
        raise HTTPException(status_code=404, detail="Collection not found.")
    queryables = copy.deepcopy(potto_collection.queryables)
    queryables["$id"] = str(
        request.url_for("api:collection-get", collection_id=collection_id)
    )
    return JSONResponse(content=queryables, media_type=MEDIA_TYPE_JSON_SCHEMA)


@router.get(
    "/collections/{collection_id}/schema",
    name="collection-get-schema",
)
async def get_collection_schema(
        request: Request,
        collection_id: str,
        potto: PottoDependency,
        user: UserDependency,
        locale: LocaleDependency,
) -> JSONResponse:
    potto_collection = await potto.api_get_collection(
        collection_id, user=user, locale=locale, include_schema=True)
    schema = copy.deepcopy(potto_collection.schema)
    schema["$id"] = str(
        request.url_for("api:collection-get", collection_id=collection_id)
    )
    return JSONResponse(content=schema, media_type=MEDIA_TYPE_JSON_SCHEMA)


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
