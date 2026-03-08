import logging

import babel
from pygeoapi.api import (
    FORMAT_TYPES,
    F_JSON,
    F_JSONLD,
    F_HTML,
)
from starlette.requests import Request
from starlette.responses import (
    JSONResponse,
    Response,
)
from starlette_babel import gettext_lazy as _

from ...config import PottoSettings
from ...operations.metadata import get_server_metadata
from ...operations import collections as collection_operations
from ...schemas.web.base import HtmlLanding
from ...schemas.pygeoapi_config import ItemCollectionConfig
from ...wrapper import Potto
from .. import util

logger = logging.getLogger(__name__)


async def get_landing_page(request: Request) -> Response:
    settings: PottoSettings = request.state.settings
    async with settings.get_db_session_maker()() as session:
        server_metadata = await get_server_metadata(session)
        db_collections, total_collections = await collection_operations.paginated_list_collections(
            session, include_total=True)
    # current_locale = babel.Locale.parse(request.state.language)
    return request.state.templates.TemplateResponse(
        request,
        "landing_page.html",
        context={
            "show_description": False,
            "data": {
                "collections": db_collections,
            },
            "has_item_collections": total_collections > 0,
            "has_stac_collections": False,
            "has_processes": False,
            "has_tiles": False,
            "pygeoapi_config": server_metadata
        }
    )


async def get_conformance_details(request: Request) -> Response:
    potto: Potto = request.state.potto
    current_locale = babel.Locale.parse(request.state.language)
    requested_format = util.get_accepted_info(request)[1]
    format_to_process = (
        requested_format if requested_format != F_HTML else F_JSON
    ) or F_JSON
    result = await potto.api_get_conformance_details()
    if requested_format == F_HTML:
        content = result.content
        conformance_url = str(request.url_for("conformance-document"))
        content["links"] = [
            {
                "href": conformance_url,
                "rel": "self",
                "title": _("This document as HTML"),
                "type": FORMAT_TYPES[F_HTML]
            },
            {
                "href": f"{conformance_url}?f={F_JSON}",
                "rel": "alternate",
                "title": _("This document as JSON"),
                "type": FORMAT_TYPES[F_JSON]
            },
            {
                "href": f"{conformance_url}?f={F_JSONLD}",
                "rel": "alternate",
                "title": _("This document as RDF (JSON-LD)"),
                "type": FORMAT_TYPES[F_JSONLD]
            },
        ]
        return request.state.templates.TemplateResponse(
            request,
            "conformance.html",
            context={
                "data": content,
                "pygeoapi_config": await potto.get_localized_config(current_locale),
            }
        )
    else:
        return JSONResponse(
            content=result.content,
            headers=result.metadata
        )


async def get_openapi_document(request: Request) -> Response:
    potto: Potto = request.state.potto
    current_locale = babel.Locale.parse(request.state.language)
    requested_format = util.get_accepted_info(request)[1]
    result = await potto.api_get_openapi_document()
    if requested_format == F_HTML:
        return request.state.templates.TemplateResponse(
            request,
            "openapi/swagger.html",
            context={
                "data": {
                    "openapi-document-path": request.url_for("openapi-document")
                },
                "pygeoapi_config": await potto.get_localized_config(current_locale),
            }
        )
    else:
        return JSONResponse(
            content=result.content,
        )
