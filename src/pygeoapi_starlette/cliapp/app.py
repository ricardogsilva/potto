import logging
from typing import Annotated

import cyclopts
import uvicorn
from cyclopts import App

from ..config import (
    get_settings,
    PygeoapiStarletteSettings,
)


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
    pygeoapi_starlette_app.console.print(
        "About to start uvicorn server with the following settings:")
    pygeoapi_starlette_app.console.print(settings.model_dump())

    # NOTE: passing `app` as a string in order to enable uvicorn's reloading
    # feature, as per:
    #
    # https://github.com/Kludex/uvicorn/discussions/2553#discussion-7774794
    #

    # FIXME: reload is not working at all when calling uvicorn programmatically
    # as per https://github.com/Kludex/uvicorn/discussions/2144
    #
    uvicorn_config = uvicorn.Config(
        "pygeoapi_starlette.webapp.app:create_app",
        factory=True,
        host=settings.bind_host,
        port=settings.bind_port,
        log_config=str(settings.log_config_file),
        log_level=logging.DEBUG if settings.debug else logging.INFO,
        reload=settings.debug,
        reload_dirs=settings.reload_dirs if settings.debug else None,
    )
    server = uvicorn.Server(uvicorn_config)
    server.run()