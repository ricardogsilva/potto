import logging
import os
import sys
from pathlib import Path
from typing import Annotated

import cyclopts
from cyclopts import App
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.traceback import install as rich_install_traceback

from ..config import (
    get_settings,
    PottoSettings,
)
from .db import db_app
from .admin import admin_app

_console = Console()
_error_console = Console(stderr=True)
potto_app = App(
    console=_console,
    error_console=_error_console,
)
rich_install_traceback(console=_error_console)
admin_app.console = _console
admin_app.error_console = _error_console
db_app.console = _console
db_app.error_console = _error_console
potto_app.command(admin_app.meta, name="admin")
potto_app.command(db_app.meta, name="db")


@potto_app.meta.default
def launcher(
    *tokens: Annotated[
        str,
        cyclopts.Parameter(show=False, allow_leading_hyphen=True)
    ],
):
    """Potto

    Custom cli launcher that injects potto's settings if needed.

    This custom launcher detects if access to the potto settings is
    being requested by the underlying CLI command and injects them if needed.

    Note that this strategy is used because we do not use cyclopts builtin
    configuration facilities, but rather pydantic-settings.
    """
    settings = get_settings()
    rich_log_handler = RichHandler(console=potto_app.error_console)
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        handlers=[rich_log_handler]
    )
    command, bound, ignored = potto_app.parse_args(tokens)
    additional_kwargs = {}
    if "settings" in ignored:
        additional_kwargs = {
            "settings": settings,
        }
    return command(*bound.args, **bound.kwargs, **additional_kwargs)


@potto_app.command(name="run-server")
def run_uvicorn_server(
        *,
        settings: Annotated[PottoSettings, cyclopts.Parameter(parse=False)],
):
    table = Table(title="Potto configuration")
    table.add_column("Parameter")
    table.add_column("Value")
    for k, v in settings.model_dump().items():
        if k == "uvicorn_num_workers" and settings.debug:
            v = "1 (reload mode)"
        table.add_row(k, str(v))
    potto_app.console.print(table)

    # NOTE: passing `app` as a string in order to enable uvicorn's reloading
    # feature, as per:
    #
    # https://github.com/Kludex/uvicorn/discussions/2553#discussion-7774794
    #

    uvicorn_args = [
        "uvicorn",
        "potto.webapp.main:create_app",
        f"--port={settings.bind_port}",
        f"--host={settings.bind_host}",
        "--factory",
        "--access-log",
    ]
    if settings.debug:
        uvicorn_args.extend(
            [
                "--reload",
                f"--reload-dir={str(Path(__file__).parents[1])}",
                "--log-level=debug",
            ]
        )
    else:
        uvicorn_args.extend(
            [
                f"--workers={settings.uvicorn_num_workers}",
                "--log-level=info",
            ]
        )

    if (log_config_file := settings.uvicorn_log_config_file) is not None:
        uvicorn_args.append(f"--log-config={str(log_config_file)}")
    if settings.public_url.startswith("https://"):
        uvicorn_args.extend(
            [
                "--forwarded-allow-ips=*",
                "--proxy-headers",
            ]
        )
    sys.stdout.flush()
    sys.stderr.flush()
    os.execvp("uvicorn", uvicorn_args)
