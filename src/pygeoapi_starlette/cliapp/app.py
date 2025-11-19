import logging
from typing import Annotated

import cyclopts
import uvicorn
from cyclopts import App

from ..config import (
    get_settings,
    PygeoapiStarletteSettings,
)
from ..webapp.app import create_app_from_settings


pygeoapi_starlette_app = App()


@pygeoapi_starlette_app.meta.default
def launcher(
    *tokens: Annotated[
        str,
        cyclopts.Parameter(show=False, allow_leading_hyphen=True)
    ],
):
    """Custom cli launcher that injects pygeoapi_starlette's settings if needed.

    This custom launcher detects if access to the pygeoapi_starlette settings is
    being requested by the underlying CLI command and injects them if needed.

    Note that this strategy is used because we do not use cyclopts builtin
    configuration facilities, but rather pydantic-settings.
    """
    command, bound, ignored = pygeoapi_starlette_app.parse_args(tokens)
    additional_kwargs = {}
    if "settings" in ignored:
        additional_kwargs = {
            "settings": get_settings(),
        }
    return command(*bound.args, **bound.kwargs, **additional_kwargs)


@pygeoapi_starlette_app.command(name="run-server")
def run_uvicorn_server(
        *,
        settings: Annotated[PygeoapiStarletteSettings, cyclopts.Parameter(parse=False)],
):
    starlette_app = create_app_from_settings(settings)
    pygeoapi_starlette_app.console.print(
        "About to start uvicorn server with the following settings:")
    pygeoapi_starlette_app.console.print(settings.model_dump())
    uvicorn_config = uvicorn.Config(
        starlette_app,
        host=settings.bind_host,
        port=settings.bind_port,
        log_config=str(settings.log_config_file),
        log_level=logging.DEBUG if settings.debug else logging.INFO,
        reload=True if settings.debug else False,
    )
    server = uvicorn.Server(uvicorn_config)
    server.run()