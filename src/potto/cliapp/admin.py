import asyncio
import inspect
from typing import (
    Annotated,
    Literal,
)

import pydantic
from rich.table import Table

from ..config import (
    get_settings,
    PottoSettings,
)
from ..schemas import cli as cli_schemas
from ..wrapper import Potto

import cyclopts

admin_app = cyclopts.App(name="admin")
collections_sub_app = cyclopts.App(name="collections")

admin_app.command(collections_sub_app, name="collection-resources")


@admin_app.meta.default
def launcher(
        *tokens: Annotated[
            str,
            cyclopts.Parameter(show=False, allow_leading_hyphen=True)
        ],
):
    """Admin-related functionality."""
    command, bound, ignored = admin_app.parse_args(tokens)
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


@collections_sub_app.command(name="list")
async def list_collection_resources(
        page: int = 1,
        page_size: int = 20,
        output_format: Literal["json", "table"] = "table",
        *,
        settings: Annotated[PottoSettings, cyclopts.Parameter(parse=False)],
) -> None:
    """List collections."""
    potto = Potto(settings)
    item_collections = await potto.list_item_collection_configs(page=page, page_size=page_size)
    if output_format == "json":
        result_adapter = pydantic.TypeAdapter(
            list[cli_schemas.ItemCollectionConfigReadListItem])
        serialized = result_adapter.dump_json(
            [
                cli_schemas.ItemCollectionConfigReadListItem(**i.model_dump())
                for i in item_collections
            ],
            indent=2,
        ).decode()
        admin_app.console.print_json(serialized)
    else:
        collection_table = Table(title="Item Collections")
        for field_name in cli_schemas.ItemCollectionConfigReadListItem.model_fields.keys():
            collection_table.add_column(field_name)
        for item_collection in item_collections:
            table_row = []
            for field_name in cli_schemas.ItemCollectionConfigReadListItem.model_fields.keys():
                table_row.append(str(getattr(item_collection, field_name)))
            collection_table.add_row(*table_row)
        serialized = collection_table
        admin_app.console.print(serialized)


@collections_sub_app.command(name="detail")
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

@collections_sub_app.command(name="create")
async def create_collection_resource(
        # collection_configuration: Annotated[cli_schemas.ItemCollectionConfigCreate, cyclopts.Parameter(name="*")],
        collection_configuration: cli_schemas.ItemCollectionConfigCreate,
        *,
        settings: Annotated[PottoSettings, cyclopts.Parameter(parse=False)],
) -> None:
    admin_app.console.print(f"{collection_configuration=}")
