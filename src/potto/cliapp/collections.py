import asyncio
import inspect
import logging
import sys
from math import ceil
from pathlib import Path
from typing import (
    Annotated,
    Literal,
)

import yaml
from rich.table import Table

from ..config import (
    get_settings,
    PottoSettings,
)
from ..exceptions import PottoException
from ..operations import collections as collection_ops
from ..schemas import cli as cli_schemas

import cyclopts
from starlette.authentication import UnauthenticatedUser

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
) -> None:
    """Import collections from pygeoapi."""
    user = UnauthenticatedUser()
    if not pygeoapi_configuration.is_file():
        raise SystemExit(f"Error: pygeoapi configuration file not found.")

    raw_config = await asyncio.to_thread(Path(pygeoapi_configuration).read_text)
    pygeoapi_config = await asyncio.to_thread(yaml.safe_load, raw_config)

    num_imported = 0
    async with settings.get_db_session_maker()() as session:
        existing_collections = await collection_ops.collect_all_collections(
            session, user)
        relevant_resources = {
            id_: res for id_, res in pygeoapi_config.get("resources", {}).items()
            if res.get("type") == "collection"
               and (resources is None or id in resources)
               and (
                       overwrite or id_ not in
                       [c.resource_identifier for c in existing_collections]
               )
        }
        for idx, (identifier, resource) in enumerate(relevant_resources.items()):
            logger.debug(
                f"[{idx+1}/{len(relevant_resources)}]Processing "
                f"collection {identifier!r}..."
            )
            try:
                await collection_ops.import_pygeoapi_collection(
                    session, user, identifier, resource, overwrite=overwrite)
                num_imported += 1
            except PottoException as err:
                collections_app.error_console.print(
                    f"Could not import collection {identifier!r} - {err}")
    collections_app.console.print(
        f"Done! Imported [{num_imported}/{len(relevant_resources)}] collections")


@collections_app.command(name="list")
async def list_collections(
        page: int = 1,
        page_size: int = 20,
        format: Literal["json", "table"] = "table",
        *,
        settings: Annotated[PottoSettings, cyclopts.Parameter(parse=False)],
) -> None:
    """List collections."""
    user = UnauthenticatedUser()
    async with settings.get_db_session_maker()() as session:
        collections, total = await collection_ops.paginated_list_collections(
            session,
            user,
            page=page,
            page_size=page_size,
            include_total=True,
        )
    result = cli_schemas.CollectionList(
        items=[cli_schemas.CollectionListItem.from_db_item(i) for i in collections],
        meta=cli_schemas.CollectionListMeta(
            page=page,
            page_size=len(collections),
            total_items=total,
            total_pages=ceil(total / page_size),
        )
    )
    if format == "json":
        collections_app.console.print_json(result.model_dump_json(indent=2))
    else:
        collection_table = Table(
            title="Collections",
            caption=f"Showing {result.meta.page_size} of {result.meta.total_items} items"
        )
        for field_name in cli_schemas.CollectionListItem.model_fields.keys():
            collection_table.add_column(field_name)
        for item_collection in result.items:
            table_row = []
            for field_name in cli_schemas.CollectionListItem.model_fields.keys():
                table_row.append(str(getattr(item_collection, field_name)))
            collection_table.add_row(*table_row)
        serialized = collection_table
        collections_app.console.print(serialized)


@collections_app.command(name="detail")
async def get_collection(
        collection_identifier: str,
        format: Literal["json", "table"] = "table",
        *,
        settings: Annotated[PottoSettings, cyclopts.Parameter(parse=False)],
) -> None:
    """Get details about a collection."""
    user = UnauthenticatedUser()
    async with settings.get_db_session_maker()() as session:
        if not (
            collection := await collection_ops.get_collection_by_resource_identifier(
                session, user, collection_identifier)
        ):
            raise SystemExit(f"Error: Collection {collection_identifier!r} not found.")
    result = cli_schemas.CollectionDetail.from_db_item(collection)
    if format == "json":
        collections_app.console.print_json(result.model_dump_json(indent=2))
    else:
        detail_table = Table(title="Collection Details")
        detail_table.add_column("property")
        detail_table.add_column("value")
        for field_name in cli_schemas.CollectionDetail.model_fields.keys():
            detail_table.add_row(field_name, str(getattr(result, field_name)))
        collections_app.console.print(detail_table)


@collections_app.command(name="delete")
async def delete_collections(
        *collection_identifier: str,
        settings: Annotated[PottoSettings, cyclopts.Parameter(parse=False)],
) -> None:
    """Delete collections."""
    user = UnauthenticatedUser()
    found_error = False
    async with settings.get_db_session_maker()() as session:
        for id_ in collection_identifier:
            if not (
                db_collection := await collection_ops.get_collection_by_resource_identifier(
                    session, user, id_)
            ):
                collections_app.error_console.print(f"Collection {id_!r} not found.")
                found_error = True
                continue
            try:
                await collection_ops.delete_collection(session, user, db_collection.id)
                collections_app.console.print(f"Collection {id_!r} deleted")
            except PottoException as err:
                collections_app.error_console.print(
                    f"Could not delete {collection_identifier!r} - {err}")
                found_error = True
                continue
    sys.exit(0 if not found_error else 1)
