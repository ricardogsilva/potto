import dataclasses
import json
import logging

import babel
import pygeoapi
import pygeoapi.api
import pygeoapi.l10n
import pygeoapi.util
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from ..requests import PygeoapiRequest
from .. import util

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class PygeoapiStructuredResponse:
    headers: dict[str, str]
    status_code: int
    json_content: str


async def home(request: Request):
    util.check_media_type(
        requested_media_type:=util.get_requested_media_type(request)
    )
    pygeoapi_response = PygeoapiStructuredResponse(
        *pygeoapi.api.landing_page(
            request.state.pygeoapi,
            PygeoapiRequest(original_request=request)
        )
    )
    content = json.loads(pygeoapi_response.json_content)

    if "html" in requested_media_type:
        html_renderer: Jinja2Templates = request.state.templates
        logger.debug(f"{request.url_for('static', path='img/favicon.ico')=}")
        return html_renderer.TemplateResponse(
            request,
            "landing_page.html",
            context={
                "data": content,
                "config": pygeoapi.l10n.translate_struct(
                    request.state.pygeoapi.config,
                    locale_=babel.Locale.parse(request.state.language),
                    is_config=True
                ),
            }
        )
    else:
        return JSONResponse(
            content=content,
            status_code=pygeoapi_response.status_code,
            headers=pygeoapi_response.headers
        )


async def get_conformance_details(request: Request):
    util.check_media_type(
        requested_media_type:=util.get_requested_media_type(request)
    )

    pygeoapi_response = PygeoapiStructuredResponse(
        *pygeoapi.api.conformance(
            request.state.pygeoapi,
            PygeoapiRequest(original_request=request)
        )
    )
    if "html" in requested_media_type:
        html_renderer: Jinja2Templates = request.state.templates
        pygeoapi_: pygeoapi.api.API = request.state.pygeoapi
        return html_renderer.TemplateResponse(
            request,
            "conformance.html",
            context={
                "config": pygeoapi_.tpl_config
            }
        )
    else:
        return JSONResponse(
            content=json.loads(pygeoapi_response.json_content),
            status_code=pygeoapi_response.status_code,
            headers=pygeoapi_response.headers
        )


routes = [
    Route("/", home),
    Route("/conformance", get_conformance_details),
]