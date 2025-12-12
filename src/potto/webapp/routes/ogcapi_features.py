import json

import babel
from jinja2 import TemplateNotFound
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
from ...schemas.items import FeatureCollectionFilter
from ...schemas.web import (
    GeoJsonItemCollection,
    JsonLdItemCollection,
    HtmlItemCollection,
)
from .. import util


async def list_collections(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    requested_format = util.get_accepted_info(request)[1]
    format_to_process = (
        (requested_format if requested_format != F_HTML else F_JSON)
        or F_JSON
    )
    potto: Potto = request.state.potto
    result = await potto.api_list_collections(
        locale=current_locale,
        output_format=format_to_process,
    )
    if requested_format == F_HTML:
        content = result.content
        content["links"] = util.set_html_link_self_relation(content["links"])
        json_ld_result = await potto.api_list_collections(
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
    result = await potto.api_get_collection(
        collection_id=collection_id,
        locale=current_locale,
        output_format=format_to_process,
    )
    if requested_format == F_HTML:
        json_ld_result = await potto.api_get_collection(
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
    potto: Potto = request.state.potto
    result = await potto.api_list_collection_items(
        collection_id=request.path_params["collection_id"],
        locale=current_locale,
        filter_=FeatureCollectionFilter.from_query_parameters(request.query_params)
    )
    if (requested_format := util.get_accepted_info(request)[1]) == F_HTML:
        # pygeoapi supports looking for templates also in the configuration
        # of the underlying resource being acted upon by looking for
        # a `templates` key in the resource configuration - potto does not
        # support this but will rather search for templates named
        # `templates/items/{collection_id}-list.html` and fallback to
        # `templates/items/list.html`
        try:
            template_path = f"items/{result.resource.identifier}-list.html"
            request.state.templates.get_template(template_path)
        except TemplateNotFound:
            template_path = f"items/list.html"
        json_ld_response_content = JsonLdItemCollection.from_potto(
            result, request.url_for)
        response_content = HtmlItemCollection.from_potto(result, request.url_for)
        return request.state.templates.TemplateResponse(
            request,
            template_path,
            context={
                "data": response_content,
                "pygeoapi_config": potto.get_localized_config(current_locale),
                "jsonld_content": json_ld_response_content.model_dump_json(by_alias=True),
            },
            headers={
                **result.metadata,
                "Content-Type": "text/html; charset=utf-8",
            }
        )
    elif requested_format == F_JSONLD:
        response_content = JsonLdItemCollection.from_potto(result, request.url_for)
        return JSONResponse(
            response_content.model_dump(by_alias=True),
            headers=result.metadata
        )
    else:
        response_content = GeoJsonItemCollection.from_potto(result, request.url_for)
        return JSONResponse(
            content=response_content.model_dump(by_alias=True),
            headers=result.metadata
        )


async def get_item_details(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    requested_format = util.get_accepted_info(request)[1]
    format_to_process = (
        (requested_format if requested_format != F_HTML else F_JSON)
        or F_JSON
    )
    potto: Potto = request.state.potto
    result = await potto.api_get_item(
        collection_id=request.path_params["collection_id"],
        item_id=request.path_params["item_id"],
        locale=current_locale,
        output_format=format_to_process,
    )
    if requested_format == F_HTML:
        raise NotImplementedError
    else:
        return JSONResponse(content=result.content, headers=result.metadata)
