import json
import logging

from starlette.requests import Request
from starlette.responses import (
    JSONResponse,
    Response,
)
import pygeoapi.api.tiles

from .. import util
from ..requests import PygeoapiRequest

logger = logging.getLogger(__name__)


async def list_tile_matrix_sets(request: Request) -> Response:
    util.check_media_type(
        requested_media_type:=util.get_requested_media_type(request)
    )
    papi_headers, papi_status_code, papi_content = pygeoapi.api.tiles.tilematrixsets(
        request.state.pygeoapi,
        PygeoapiRequest(original_request=request)
    )
    content = json.loads(papi_content)
    if "html" in requested_media_type:
        content["links"] = util.set_html_link_self_relation(content["links"])
        return request.state.templates.TemplateResponse(
            request,
            "tilematrixsets/list.html",
            context={
                "data": content,
                "config": util.get_localized_pygeoapi_config(
                    request.state.pygeoapi.config, request.state.language),
            }
        )
    else:
        return JSONResponse(
            content=content,
            status_code=papi_status_code,
            headers=papi_headers
        )

