import logging

import babel
from jinja2 import TemplateNotFound
from starlette.requests import Request
from starlette.responses import Response

from ...operations import collections as collection_operations
from ...schemas.web import items

from ...config import PottoSettings
from ...wrapper import Potto

logger = logging.getLogger(__name__)


async def list_collections(request: Request) -> Response:
    # current_locale = babel.Locale.parse(request.state.language)
    settings: PottoSettings = request.state.settings
    async with settings.get_db_session_maker()() as session:
        db_collections, total = await collection_operations.paginated_list_collections(
            session, include_total=True)
    return request.state.templates.TemplateResponse(
        request,
        "collections/list.html",
        context={
            "items": db_collections,
        }
    )


async def get_collection_details(request: Request) -> Response:
    # current_locale = babel.Locale.parse(request.state.language)
    settings: PottoSettings = request.state.settings
    collection_id = request.path_params["collection_id"]
    async with settings.get_db_session_maker()() as session:
        db_collection = await collection_operations.get_collection_by_resource_identifier(
            session, collection_id)
    return request.state.templates.TemplateResponse(
        request,
        "collections/detail.html",
        context={
            "item": db_collection,
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
