import json
import logging

import babel
from jinja2 import TemplateNotFound
from pygeoapi.api import (
    F_JSONLD,
)
from starlette.requests import Request
from starlette.responses import Response

from ... import constants
from ...schemas.web.collections import (
    HtmlItemCollection,
    HtmlItemFeature,
    JsonLdItemCollection,
)

from ...config import PottoSettings
from ...wrapper import Potto
from ...schemas.collections import FeatureFilter
from .. import util

logger = logging.getLogger(__name__)


async def list_collections(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    settings: PottoSettings = request.state.settings
    potto = Potto(settings)
    result = await potto.api_list_collections(
        locale=current_locale,
        output_format=constants.PYGEOAPI_F_JSON,
    )
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
            "pygeoapi_config": await potto.get_localized_config(current_locale),
            "jsonld_content": json.dumps(json_ld_result.content),
        }
    )


async def get_collection_details(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    potto: Potto = request.state.potto
    collection_id = request.path_params["collection_id"]
    result = await potto.api_get_collection(
        collection_id=collection_id,
        locale=current_locale,
        output_format=constants.PYGEOAPI_F_JSON,
    )
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
            "pygeoapi_config": await potto.get_localized_config(current_locale),
            "jsonld_content": json.dumps(json_ld_result.content),
        }
    )


async def list_collection_items(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    potto: Potto = request.state.potto
    result = await potto.api_list_collection_items(
        collection_id=request.path_params["collection_id"],
        locale=current_locale,
        filter_=FeatureFilter.from_query_parameters(request.query_params)
    )
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
            "pygeoapi_config": await potto.get_localized_config(current_locale),
            "jsonld_content": json_ld_response_content.model_dump_json(by_alias=True),
        },
        headers={
            **result.metadata,
            "Content-Type": "text/html; charset=utf-8",
        }
    )


async def get_item_details(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    potto: Potto = request.state.potto
    result = await potto.api_get_item(
        collection_id=request.path_params["collection_id"],
        item_id=request.path_params["item_id"],
        locale=current_locale,
    )
    logger.debug(f"{result=}")
    # pygeoapi supports looking for templates also in the configuration
    # of the underlying resource being acted upon by looking for
    # a `templates` key in the resource configuration - potto does not
    # support this but will rather search for templates named
    # `templates/items/{collection_id}-item-feature.html` and fallback to
    # `templates/items/item-feature.html`
    try:
        template_path = f"items/{result.resource.identifier}-item-feature.html"
        request.state.templates.get_template(template_path)
    except TemplateNotFound:
        template_path = f"items/item-feature.html"

    response_content = HtmlItemFeature.from_potto(result, request.url_for)
    return request.state.templates.TemplateResponse(
        request,
        template_path,
        context={
            "data": response_content,
            "pygeoapi_config": await potto.get_localized_config(current_locale),
        },
        headers={
            **result.metadata,
            "Content-Type": "text/html; charset=utf-8",
        }
    )
