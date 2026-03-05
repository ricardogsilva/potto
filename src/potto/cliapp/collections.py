import asyncio
import inspect
import logging
from pathlib import Path
from typing import (
    Annotated,
    Literal,
)

import pydantic
import yaml
from rich.table import Table

from ..config import (
    get_settings,
    PottoSettings,
)
from ..exceptions import PottoException
from ..operations.collections import import_pygeoapi_collection
from ..schemas import cli as cli_schemas
from ..wrapper import Potto
from ..db.queries import collect_all_collections

import cyclopts

collections_app = cyclopts.App()
logger = logging.getLogger(__name__)


@collections_app.meta.default
def launcher(
        *tokens: Annotated[
            str,
            cyclopts.Parameter(show=False, allow_leading_hyphen=True)
        ],
):
    """Collection-related functionality."""
    command, bound, ignored = collections_app.parse_args(tokens)
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


@collections_app.command(name="import-from-pygeoapi")
async def import_collections_from_pygeoapi(
        pygeoapi_configuration: Path,
        resources: list[str] | None = None,
        overwrite: bool = False,
        *,
        settings: Annotated[PottoSettings, cyclopts.Parameter(parse=False)],
):
    """Import collections from pygeoapi."""
    if not pygeoapi_configuration.is_file():
        raise SystemExit(f"Error: pygeoapi configuration file not found.")

    raw_config = await asyncio.to_thread(Path(pygeoapi_configuration).read_text)
    pygeoapi_config = await asyncio.to_thread(yaml.safe_load, raw_config)

    num_imported = 0
    async with settings.get_db_session_maker()() as session:
        existing_collections = await collect_all_collections(session)
        relevant_resources = {
            id_: res for id_, res in pygeoapi_config.get("resources", {}).items()
            if res.get("type") == "collection"
               and (resources is None or id in resources)
               and (overwrite or id_ not in [c.resource_identifier for c in existing_collections])
        }
        for idx, (identifier, resource) in enumerate(relevant_resources.items()):
            logger.debug(f"[{idx+1}/{len(relevant_resources)}]Processing collection {identifier!r}...")
            try:
                await import_pygeoapi_collection(session, identifier, resource, overwrite=overwrite)
                num_imported += 1
            except PottoException as err:
                collections_app.error_console.print(f"Could not import collection {identifier!r} - {err}")
    collections_app.console.print(f"Done! Imported [{num_imported}/{len(relevant_resources)}] collections")


@collections_app.command(name="list")
async def list_collections(
        page: int = 1,
        page_size: int = 20,
        output_format: Literal["json", "table"] = "table",
        *,
        settings: Annotated[PottoSettings, cyclopts.Parameter(parse=False)],
) -> None:
    """List collections."""
    potto = Potto(settings)
    collections = await potto.list_item_collection_configs(page=page, page_size=page_size)
    if output_format == "json":
        result_adapter = pydantic.TypeAdapter(
            list[cli_schemas.ItemCollectionConfigReadListItem])
        serialized = result_adapter.dump_json(
            [
                cli_schemas.ItemCollectionConfigReadListItem(**i.model_dump())
                for i in collections
            ],
            indent=2,
        ).decode()
        collections_app.console.print_json(serialized)
    else:
        collection_table = Table(title="Item Collections")
        for field_name in cli_schemas.ItemCollectionConfigReadListItem.model_fields.keys():
            collection_table.add_column(field_name)
        for item_collection in collections:
            table_row = []
            for field_name in cli_schemas.ItemCollectionConfigReadListItem.model_fields.keys():
                table_row.append(str(getattr(item_collection, field_name)))
            collection_table.add_row(*table_row)
        serialized = collection_table
        collections_app.console.print(serialized)


@collections_app.command(name="detail")
async def get_collection_resource(
        collection_identifier: str,
        output_format: Literal["json", "table"] = "table",
        *,
        settings: Annotated[PottoSettings, cyclopts.Parameter(parse=False)],
) -> None:
    """Get details about a collection configuration."""
    potto = Potto(settings)
    if not (collection_detail := await potto.get_item_collection_config(collection_identifier)):
        raise SystemExit(f"Error: Collection {collection_identifier!r} not found.")
    if output_format == "json":
        admin_app.console.print_json(
            cli_schemas.ItemCollectionConfigRead(
                **collection_detail.model_dump()
            ).model_dump_json(indent=2)
        )
    else:
        detail_table = Table(title="Item Collection Details")
        detail_table.add_column("property")
        detail_table.add_column("value")
        for field_name in cli_schemas.ItemCollectionConfigRead.model_fields.keys():
            detail_table.add_row(field_name, str(getattr(collection_detail, field_name)))
        admin_app.console.print(detail_table)

@collections_app.command(name="create")
async def create_collection_resource(
        # collection_configuration: Annotated[cli_schemas.ItemCollectionConfigCreate, cyclopts.Parameter(name="*")],
        collection_configuration: cli_schemas.ItemCollectionConfigCreate,
        *,
        settings: Annotated[PottoSettings, cyclopts.Parameter(parse=False)],
) -> None:
    admin_app.console.print(f"{collection_configuration=}")
