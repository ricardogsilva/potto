import json

import babel
from pygeoapi.api import (
    F_HTML,
    F_JSON,
    F_JSONLD,
)
from starlette.requests import Request
from starlette.responses import (
    JSONResponse,
    Response,
)

from ...wrapper import Potto
from .. import util


async def list_collections(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    requested_format = util.get_accepted_info(request)[1]
    format_to_process = (
        (requested_format if requested_format != F_HTML else F_JSON)
        or F_JSON
    )
    potto: Potto = request.state.potto
    result = await potto.list_collections(
        locale=current_locale,
        output_format=format_to_process,
    )
    if requested_format == F_HTML:
        content = result.content
        content["links"] = util.set_html_link_self_relation(content["links"])
        json_ld_result = await potto.list_collections(
            locale=current_locale,
            output_format=F_JSONLD,
        )
        return request.state.templates.TemplateResponse(
            request,
            "collections/list.html",
            context={
                "data": content,
                "pygeoapi_config": potto.get_localized_config(current_locale),
                "jsonld_content": json.dumps(json_ld_result.content),
            }
        )
    else:
        return JSONResponse(content=result.content, headers=result.metadata)


async def get_collection_details(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    requested_format = util.get_accepted_info(request)[1]
    format_to_process = (
        (requested_format if requested_format != F_HTML else F_JSON)
        or F_JSON
    )
    potto: Potto = request.state.potto
    collection_id = request.path_params["collection_id"]
    result = await potto.get_collection(
        collection_id=collection_id,
        locale=current_locale,
        output_format=format_to_process,
    )
    if requested_format == F_HTML:
        json_ld_result = await potto.get_collection(
            collection_id=collection_id,
            locale=current_locale,
            output_format=F_JSONLD,
        )
        content = result.content
        content["links"] = util.set_html_link_self_relation(content["links"])
        return request.state.templates.TemplateResponse(
            request,
            "collections/detail.html",
            context={
                "data": content,
                "pygeoapi_config": potto.get_localized_config(current_locale),
                "jsonld_content": json.dumps(json_ld_result.content),
            }
        )
    else:
        return JSONResponse(content=result.content, headers=result.metadata)


async def list_collection_items(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    requested_format = util.get_accepted_info(request)[1]
    format_to_process = (
        (requested_format if requested_format != F_HTML else F_JSON)
        or F_JSON
    )
    potto: Potto = request.state.potto
    result = await potto.list_collection_items(
        collection_id=request.path_params["collection_id"],
        bbox=request.query_params.get("bbox"),
        bbox_crs=request.query_params.get("bbox-crs"),
        crs=request.query_params.get("crs"),
        datetime_filter=request.query_params.get("datetime"),
        filter_=request.query_params.get("filter"),
        filter_crs=request.query_params.get("filter-crs"),
        filter_lang=request.query_params.get("filter-lang"),
        limit=request.query_params.get("limit"),
        locale=current_locale,
        offset=int(request.query_params.get("offset", 0)),
        output_format=format_to_process,
        properties=dict(request.query_params),
        query_param=request.query_params.get("q"),
        result_type=request.query_params.get("resulttype"),
        sort_by=request.query_params.get("sortby"),
        skip_geometry=(
            True
            if request.query_params.get("skipGeometry", "").lower()
               in ("true", "yes", "on", "t", "1") else False
        ),
    )
    if requested_format == F_HTML:
        raise NotImplementedError
    else:
        return JSONResponse(content=result.content, headers=result.metadata)


async def get_item_details(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    requested_format = util.get_accepted_info(request)[1]
    format_to_process = (
        (requested_format if requested_format != F_HTML else F_JSON)
        or F_JSON
    )
    potto: Potto = request.state.potto
    result = await potto.get_item(
        collection_id=request.path_params["collection_id"],
        item_id=request.path_params["item_id"],
        locale=current_locale,
        output_format=format_to_process,
    )
    if requested_format == F_HTML:
        raise NotImplementedError
    else:
        return JSONResponse(content=result.content, headers=result.metadata)
