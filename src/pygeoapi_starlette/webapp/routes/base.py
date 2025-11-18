import json
import logging

import pygeoapi.api
from starlette.requests import Request
from starlette.responses import (
    JSONResponse,
    Response,
)
from starlette_babel import gettext_lazy as _

from ...pygeoapi_config import PygeoapiConfig
from ..requests import PygeoapiRequest
from .. import util

logger = logging.getLogger(__name__)


async def home(request: Request) -> Response:
    util.check_media_type(
        requested_media_type:=util.get_requested_media_type(request)
    )
    papi_headers, papi_status_code, papi_content = pygeoapi.api.landing_page(
        request.state.pygeoapi,
        PygeoapiRequest(
            original_request=request,
        )
    )
    content = json.loads(papi_content)

    if "html" in requested_media_type:
        content["links"] = util.set_html_link_self_relation(content["links"])
        _, _, json_ld_response = pygeoapi.api.landing_page(
            request.state.pygeoapi,
            PygeoapiRequest(
                original_request=request,
                output_format=pygeoapi.api.F_JSONLD
            )
        )
        pygeoapi_config: PygeoapiConfig = request.state.pygeoapi_config

        return request.state.templates.TemplateResponse(
            request,
            "landing_page.html",
            context={
                "data": content,
                "has_item_collections": pygeoapi_config.has_item_collection_resources(),
                "has_stac_collections": pygeoapi_config.has_stac_collection_resources(),
                "has_processes": pygeoapi_config.has_process_resources(),
                "has_tiles": pygeoapi_config.has_tiles(),
                "pygeoapi_config": pygeoapi_config.localize(request.state.language),
                "jsonld_content": json_ld_response,
            }
        )
    else:
        return JSONResponse(
            content=content,
            status_code=papi_status_code,
            headers=papi_headers
        )


async def get_conformance_details(request: Request) -> Response:
    util.check_media_type(
        requested_media_type:=util.get_requested_media_type(request)
    )

    papi_headers, papi_status_code, papi_content = pygeoapi.api.conformance(
        request.state.pygeoapi,
        PygeoapiRequest(original_request=request)
    )
    content = json.loads(papi_content)

    if "html" in requested_media_type:
        conformance_url = str(request.url_for("conformance-document"))
        content["links"] = [
            {
                "href": conformance_url,
                "rel": "self",
                "title": _("This document as HTML"),
                "type": pygeoapi.api.FORMAT_TYPES[pygeoapi.api.F_HTML]
            },
            {
                "href": conformance_url,
                "rel": "alternate",
                "title": _("This document as JSON"),
                "type": pygeoapi.api.FORMAT_TYPES[pygeoapi.api.F_JSON]
            },
            {
                "href": conformance_url,
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
                "pygeoapi_config": request.state.pygeoapi_config.localize(
                    request.state.language),
            }
        )
    else:
        return JSONResponse(
            content=content,
            status_code=papi_status_code,
            headers=papi_headers
        )


async def get_openapi_document(request: Request) -> Response:
    util.check_media_type(
        requested_media_type:=util.get_requested_media_type(request)
    )
    if "html" in requested_media_type:
        template = (
            "openapi/redoc.html"
            if request.query_params.get("ui") == "redoc"
            else "openapi/swagger.html"
        )
        return request.state.templates.TemplateResponse(
            request,
            template,
            context={
                "data": {
                    "openapi-document-path": request.url_for("openapi-document")
                },
                "pygeoapi_config": request.state.pygeoapi_config.localize(
                    request.state.language),
            }
        )
    else:
        return JSONResponse(
            content=request.state.pygeoapi.openapi,
            status_code=200,
        )
