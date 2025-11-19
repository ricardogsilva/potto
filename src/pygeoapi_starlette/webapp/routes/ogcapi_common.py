import json
import logging

import babel
import pygeoapi.api
from starlette.requests import Request
from starlette.responses import (
    JSONResponse,
    Response,
)
from starlette_babel import gettext_lazy as _

from ...pygeoapi import PygeoapiStarlette
from .. import util

logger = logging.getLogger(__name__)


async def get_landing_page(request: Request) -> Response:
    api_: PygeoapiStarlette = request.state.pygeoapi
    requested_format = util.get_accepted_info(request)[1]
    format_to_process = (
        requested_format
        if requested_format != pygeoapi.api.F_HTML
        else pygeoapi.api.F_JSON
    ) or pygeoapi.api.F_JSON
    current_locale = babel.Locale.parse(request.state.language)
    result = await api_.get_landing_page(
        locale=current_locale,
        output_format=format_to_process,
    )
    if requested_format == pygeoapi.api.F_HTML:
        content = result.content
        content["links"] = util.set_html_link_self_relation(content["links"])
        json_ld_result = await api_.get_landing_page(
            locale=current_locale,
            output_format=pygeoapi.api.F_JSONLD
        )
        return request.state.templates.TemplateResponse(
            request,
            "landing_page.html",
            context={
                "data": content,
                "has_item_collections": api_.has_item_collection_resources(),
                "has_stac_collections": api_.has_stac_collection_resources(),
                "has_processes": api_.has_process_resources(),
                "has_tiles": api_.has_tiles(),
                "pygeoapi_config": api_.get_localized_config(current_locale),
                "jsonld_content": json.dumps(json_ld_result.content),
            }
        )
    else:
        return JSONResponse(
            content=result.content,
            status_code=200,
            headers=result.metadata
        )


async def get_conformance_details(request: Request) -> Response:
    api_: PygeoapiStarlette = request.state.pygeoapi
    current_locale = babel.Locale.parse(request.state.language)
    requested_format = util.get_accepted_info(request)[1]
    format_to_process = (
        requested_format
        if requested_format != pygeoapi.api.F_HTML
        else pygeoapi.api.F_JSON
    ) or pygeoapi.api.F_JSON
    result = await api_.get_conformance_details(
        locale=current_locale,
        output_format=format_to_process,
    )
    if requested_format == pygeoapi.api.F_HTML:
        content = result.content
        conformance_url = str(request.url_for("conformance-document"))
        content["links"] = [
            {
                "href": conformance_url,
                "rel": "self",
                "title": _("This document as HTML"),
                "type": pygeoapi.api.FORMAT_TYPES[pygeoapi.api.F_HTML]
            },
            {
                "href": f"{conformance_url}?f={pygeoapi.api.F_JSON}",
                "rel": "alternate",
                "title": _("This document as JSON"),
                "type": pygeoapi.api.FORMAT_TYPES[pygeoapi.api.F_JSON]
            },
            {
                "href": f"{conformance_url}?f={pygeoapi.api.F_JSONLD}",
                "rel": "alternate",
                "title": _("This document as RDF (JSON-LD)"),
                "type": pygeoapi.api.FORMAT_TYPES[pygeoapi.api.F_JSONLD]
            },
        ]
        return request.state.templates.TemplateResponse(
            request,
            "conformance.html",
            context={
                "data": content,
                "pygeoapi_config": api_.get_localized_config(current_locale),
            }
        )
    else:
        return JSONResponse(
            content=result.content,
            headers=result.metadata
        )


async def get_openapi_document(request: Request) -> Response:
    api_: PygeoapiStarlette = request.state.pygeoapi
    current_locale = babel.Locale.parse(request.state.language)
    requested_format = util.get_accepted_info(request)[1]
    result = await api_.get_openapi_document()
    if requested_format == pygeoapi.api.F_HTML:
        return request.state.templates.TemplateResponse(
            request,
            "openapi/swagger.html",
            context={
                "data": {
                    "openapi-document-path": request.url_for("openapi-document")
                },
                "pygeoapi_config": api_.get_localized_config(current_locale),
            }
        )
    else:
        return JSONResponse(
            content=result.content,
        )
