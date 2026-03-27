import json
import logging

import babel
from jinja2 import TemplateNotFound
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer
from starlette.requests import Request
from starlette.responses import Response

from ...operations import collections as collection_operations
from ...schemas.web import items
from ...schemas import auth as auth_schemas

from ...config import PottoSettings
from ...wrapper import Potto

logger = logging.getLogger(__name__)

_PYGMENTS_FORMATTER = HtmlFormatter(style="friendly")


async def list_collections(request: Request) -> Response:
    user = (
        potto_user
        if isinstance(
            (potto_user := request.user), auth_schemas.PottoUser)
        else None
    )
    potto: Potto = request.state.potto
    return request.state.templates.TemplateResponse(
        request,
        "collections/list.html",
        context={
            "contents": await potto.api_list_collections(
                user=user,
                locale=babel.Locale.parse(request.state.language),
                page=int(request.query_params.get("page", 1)),
                page_size=int(request.query_params.get("page_size", 20)),
            ),
        }
    )


async def get_collection_details(request: Request) -> Response:
    user = (
        potto_user
        if isinstance(
            (potto_user := request.user), auth_schemas.PottoUser)
        else None
    )
    potto: Potto = request.state.potto
    contents = await potto.api_get_collection(
        request.path_params["collection_id"],
        user=user,
        locale=babel.Locale.parse(request.state.language),
        include_queryables=True,
        include_schema=True,
    )
    queryables_html = (
        highlight(json.dumps(contents.queryables, indent=2), JsonLexer(), _PYGMENTS_FORMATTER)
        if contents.queryables else None
    )
    schema_html = (
        highlight(json.dumps(contents.schema, indent=2), JsonLexer(), _PYGMENTS_FORMATTER)
        if contents.schema else None
    )
    return request.state.templates.TemplateResponse(
        request,
        "collections/detail.html",
        context={
            "contents": contents,
            "queryables_html": queryables_html,
            "schema_html": schema_html,
            "pygments_css": _PYGMENTS_FORMATTER.get_style_defs(".highlight"),
        }
    )


async def list_collection_items(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    potto: Potto = request.state.potto
    result = await potto.api_list_collection_items(
        collection_id=request.path_params["collection_id"],
        locale=current_locale,
        filter_=items.FeatureFilter.from_query_parameters(request.query_params)
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
    response_content = items.HtmlItemCollection.from_potto(result, request.url_for)
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


async def get_item_details(request: Request) -> Response:
    current_locale = babel.Locale.parse(request.state.language)
    potto: Potto = request.state.potto
    result = await potto.api_get_collection_item(
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

    response_content = items.HtmlItemFeature.from_potto(result, request.url_for)
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
