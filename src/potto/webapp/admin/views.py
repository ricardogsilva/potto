import logging
from typing import cast, Any, Dict

import pydantic
from starlette.requests import Request
from starlette_admin import BaseField, RequestAction

from starlette_admin.contrib.sqlmodel import ModelView
from starlette_admin.fields import (
    CollectionField,
    EnumField,
    JSONField,
    ListField,
    StringField,
    URLField,
)

from ...config import PottoSettings
from ...db.models import Collection
from ...db.commands import collections as collection_commands
from ...db.queries import collections as collection_queries
from ...schemas.base import PygeoapiProviderType
from ...schemas.collections import (
    CollectionCreate,
    CollectionUpdate,
)
from .fields import SpatialExtentField

logger = logging.getLogger(__name__)


class _PottoAdminModelView(ModelView):

    def handle_exception(self, exc: Exception) -> None:
        logger.exception("An error occurred", exc)
        return super().handle_exception(exc)


class CollectionItemView(_PottoAdminModelView):
    """Custom starlette-admin view for managing collections

    This view overrides both the `create` and `edit` methods in order to ensure they
    use our own commands, thus ensuring a consistent schema is preserved whether modifications
    are done via the admin UI, the web API or the CLI.
    """
    fields = (
        Collection.resource_identifier,
        Collection.collection_type,
        Collection.is_public,
        Collection.title,
        Collection.description,
        SpatialExtentField(name="spatial_extent"),
        Collection.temporal_extent_begin,
        Collection.temporal_extent_end,
        Collection.keywords,
        # JSONField(name="providers"),
        ListField(
            CollectionField(
                name="providers",
                fields=(
                    EnumField(
                        name="type",
                        enum=PygeoapiProviderType,
                    ),
                    StringField(name="python_callable"),
                    JSONField(name="config"),
                )
            )
        ),
        ListField(
            CollectionField(
                name="additional_links",
                fields=(
                    StringField(name="media_type"),
                    StringField(name="rel"),
                    URLField(name="href"),
                    JSONField(name="title"),
                    StringField(name="href_lang"),
                )
            )
        ),
    )

    exclude_fields_from_list = (
        "description",
        "additional_links",
        "keywords",
        "spatial_extent",
        "temporal_extent_begin",
        "temporal_extent_end",
        "providers",
    )

    async def serialize_field_value(
        self, value: list[dict], field: BaseField, action: RequestAction, request: Request
    ) -> Any:
        if field.name == "providers":
            result = []
            for type_, prov in value.items():
                result.append(
                    {
                        "type": PygeoapiProviderType(type_),
                        "python_callable": prov["python_callable"],
                        "config": prov["config"],
                    }
                )
            return result
        else:
            return await super().serialize_field_value(value, field, action, request)

    async def edit(self, request: Request, pk: Any, data: Dict[str, Any]) -> Any:
        data["providers"] = self._adapt_request_providers_to_internal_model(data["providers"])
        settings = cast(PottoSettings, request.app.state.SETTINGS)
        async with settings.get_db_session_maker()() as session:
            db_collection = await collection_queries.get_collection(session, int(pk))
            if db_collection is None:
                raise RuntimeError(f"Collection {pk} not found")
            try:
                return await collection_commands.update_collection(
                    session,
                    db_collection,
                    to_update=CollectionUpdate(**data),
                )
            except pydantic.ValidationError as err:
                return self.handle_exception(err)

    async def create(self, request: Request, data: dict[str, Any]) -> Any:
        data["providers"] = self._adapt_request_providers_to_internal_model(data["providers"])
        settings = cast(PottoSettings, request.app.state.SETTINGS)
        async with settings.get_db_session_maker()() as session:
            try:
                return await collection_commands.create_collection(
                    session,
                    to_create=CollectionCreate(**data)
                )
            except pydantic.ValidationError as err:
                return self.handle_exception(err)

    def _adapt_request_providers_to_internal_model(
            self, request_providers: list[dict]) -> dict[str, dict]:
        new_providers = {}
        for sent_provider in request_providers:
            new_providers[sent_provider.pop("type")] = sent_provider
        return new_providers
