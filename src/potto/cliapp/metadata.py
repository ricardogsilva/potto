import asyncio
import inspect
import logging
from typing import Annotated

import cyclopts

from ..config import (
    get_settings,
    PottoSettings,
)
from ..operations.metadata import get_server_metadata


metadata_app = cyclopts.App()
logger = logging.getLogger(__name__)


@metadata_app.meta.default
def launcher(
        *tokens: Annotated[
            str,
            cyclopts.Parameter(show=False, allow_leading_hyphen=True)
        ],
):
    """Manage server metadata."""
    command, bound, ignored = metadata_app.parse_args(tokens)
    additional_kwargs = {}
    if "settings" in ignored:
        additional_kwargs = {
            "settings": get_settings(),
        }
    if not inspect.iscoroutinefunction(command):
        return command(*bound.args, **bound.kwargs, **additional_kwargs)
    else:
        if bound is None:
            return asyncio.run(command(**additional_kwargs))
        else:
            return asyncio.run(command(*bound.args, **bound.kwargs, **additional_kwargs))


@metadata_app.command(name="detail")
async def get_metadata_detail(
        *,
        settings: Annotated[PottoSettings, cyclopts.Parameter(parse=False)],
):
    """Inspect current server metadata."""
    async with settings.get_db_session_maker()() as session:
        metadata = await get_server_metadata(session)
        metadata_app.console.print_json(metadata.model_dump_json(indent=2))
