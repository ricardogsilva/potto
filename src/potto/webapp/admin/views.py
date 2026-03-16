import logging
from typing import (
    Any,
    cast,
)

import pydantic
from starlette.requests import Request
from starlette_admin import (
    BaseField,
    RequestAction,
)
from starlette_admin.contrib.sqlmodel import ModelView
from starlette_admin.fields import (
    CollectionField,
    EnumField,
    HasMany,
    HasOne,
    JSONField,
    ListField,
    PasswordField,
    StringField,
    URLField,
)

from ...config import PottoSettings
from ...operations import collections as collection_operations
from ...db.models import (
    Collection,
    User,
)
from ...db.commands import (
    auth as auth_commands,
    collections as collection_commands,
)
from ...db.queries import (
    auth as auth_queries,
    collections as collection_queries,
)
from ...exceptions import PottoException
from ...schemas.base import PygeoapiProviderType
from ...schemas.collections import (
    CollectionCreate,
    CollectionUpdate,
)
from ...schemas.auth import (
    PottoUser,
    UserCreate,
    UserUpdate,
)
from .fields import SpatialExtentField

logger = logging.getLogger(__name__)


class _PottoAdminModelView(ModelView):

    def handle_exception(self, exc: Exception) -> None:
        logger.exception("An error occurred", exc)
        return super().handle_exception(exc)


class UserView(_PottoAdminModelView):
    """Custom starlette-admin view for managing local users

    This view overrides both the `create` and `edit` methods in order to ensure they
    use our own db commands, thus ensuring a consistent schema is preserved whether modifications
    are done via the admin UI, the web API or the CLI.
    """
    fields = (
        User.username,
        User.email,
        User.is_active,
        User.scopes,
        PasswordField("password"),
    )
    exclude_fields_from_detail = (
        "password",
    )
    exclude_fields_from_list = (
        "password",
    )

    async def create(self, request: Request, data: dict[str, Any]) -> Any:
        settings = cast(PottoSettings, request.app.state.SETTINGS)
        async with settings.get_db_session_maker()() as session:
            try:
                return await auth_commands.create_user(
                    session,
                    to_create=UserCreate(
                        **{
                            k: v for k, v in {
                                "username": data["username"],
                                "is_active": data["is_active"],
                                "email": data["email"] or None,
                                "scopes": data["scopes"] or None,
                                "password": data["password"],
                                }.items()
                            if v is not None
                        }
                    ),
                )
            except pydantic.ValidationError as err:
                self.handle_exception(err)

    async def edit(self, request: Request, pk: Any, data: dict[str, Any]) -> Any:
        settings = cast(PottoSettings, request.app.state.SETTINGS)
        async with settings.get_db_session_maker()() as session:
            if (db_user := await auth_queries.get_user(session, pk)) is None:
                raise RuntimeError(f"User {pk} not found")
            try:
                return await auth_commands.update_user(
                    session,
                    db_user,
                    to_update=UserUpdate(
                        **{
                            k: v for k,v in {
                                "username": data["username"],
                                "is_active": data["is_active"],
                                "email": data["email"] or None,
                                "scopes": data["scopes"] or None,
                                "password": data["password"],
                            }.items() if v is not None
                        }
                    ),
                )
            except pydantic.ValidationError as err:
                return self.handle_exception(err)


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
        HasOne("owner", identity="user"),
        HasMany("editors", identity="user"),
        HasMany("viewers", identity="user"),
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
        "editors",
        "viewers",
    )
    exclude_fields_from_create = ("editors", "viewers")

    async def is_row_action_allowed(self, request: Request, name: str) -> bool:
        if name in ("edit", "delete"):
            pk = request.path_params.get("pk")
            if pk is not None:
                user = cast(PottoUser, request.user)
                settings = cast(PottoSettings, request.app.state.SETTINGS)
                auth_backend = settings.get_authorization_backend()
                async with settings.get_db_session_maker()() as session:
                    collection = await collection_queries.get_collection(session, int(pk))
                if collection is not None:
                    return await auth_backend.can_edit_collection(user, collection)
        return await super().is_row_action_allowed(request, name)

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        user = cast(PottoUser, request.user)
        settings = cast(PottoSettings, request.app.state.SETTINGS)
        auth_backend = settings.get_authorization_backend()
        async with settings.get_db_session_maker()() as session:
            collection = await collection_queries.get_collection(session, int(pk))
            if collection is None:
                return None
            if not await auth_backend.can_view_collection(user, collection):
                return None
            editors = await collection_queries.get_collection_editors(
                session, collection.resource_identifier
            )
            viewers = await collection_queries.get_collection_viewers(
                session, collection.resource_identifier
            )
        object.__setattr__(collection, "editors", editors)
        object.__setattr__(collection, "viewers", viewers)
        return collection

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: Any = None,
        order_by: list[str] | None = None,
    ) -> list[Any]:
        user = cast(PottoUser, request.user)
        settings = cast(PottoSettings, request.app.state.SETTINGS)
        auth_backend = settings.get_authorization_backend()
        async with settings.get_db_session_maker()() as session:
            accessible_ids = await auth_backend.get_accessible_collection_identifiers(user)
            if accessible_ids is None:
                items, _ = await collection_queries.list_collections(
                    session,
                    offset=skip,
                    limit=limit,
                    is_public_filter=None,
                )
            else:
                items, _ = await collection_queries.list_collections(
                    session,
                    offset=skip,
                    limit=limit,
                    user_id=user.id,
                    accessible_identifiers=accessible_ids,
                )
        return items

    async def count(self, request: Request, where: Any = None) -> int:
        user = cast(PottoUser, request.user)
        settings = cast(PottoSettings, request.app.state.SETTINGS)
        auth_backend = settings.get_authorization_backend()
        async with settings.get_db_session_maker()() as session:
            accessible_ids = await auth_backend.get_accessible_collection_identifiers(user)
            if accessible_ids is None:
                _, total = await collection_queries.list_collections(
                    session,
                    limit=1,
                    is_public_filter=None,
                    include_total=True,
                )
            else:
                _, total = await collection_queries.list_collections(
                    session,
                    limit=1,
                    user_id=user.id,
                    accessible_identifiers=accessible_ids,
                    include_total=True,
                )
        return total or 0

    async def serialize(self, obj: Any, request: Request, action: RequestAction, **kwargs: Any) -> Any:
        result = await super().serialize(obj, request, action, **kwargs)
        if action == RequestAction.LIST:
            user = cast(PottoUser, request.user)
            settings = cast(PottoSettings, request.app.state.SETTINGS)
            auth_backend = settings.get_authorization_backend()
            result["_meta"]["can_edit"] = await auth_backend.can_edit_collection(user, obj)
        return result

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

    async def edit(self, request: Request, pk: Any, data: dict[str, Any]) -> Any:
        user = cast(PottoUser, request.user)
        data["providers"] = self._adapt_request_providers_to_internal_model(data["providers"])
        new_editor_ids = set(data.pop("editors", None) or [])
        new_viewer_ids = set(data.pop("viewers", None) or [])
        logger.debug(f"{data=}")
        to_set = {
            **{k: v for k, v in data.items() if k != "owner"},
            "owner_id": data.get("owner"),
        }
        settings = cast(PottoSettings, request.app.state.SETTINGS)
        auth_backend = settings.get_authorization_backend()
        async with settings.get_db_session_maker()() as session:
            db_collection = await collection_queries.get_collection(session, int(pk))
            if db_collection is None:
                raise RuntimeError(f"Collection {pk} not found")
            if not await auth_backend.can_edit_collection(user, db_collection):
                raise PottoException(f"User does not have permission to edit collection {pk}.")
            try:
                result = await collection_commands.update_collection(
                    session,
                    db_collection,
                    to_update=CollectionUpdate(
                        **{k: v for k, v in to_set.items() if v is not None},
                    ),
                )
            except pydantic.ValidationError as err:
                return self.handle_exception(err)
            current_editors = await collection_queries.get_collection_editors(
                session, db_collection.resource_identifier
            )
            current_viewers = await collection_queries.get_collection_viewers(
                session, db_collection.resource_identifier
            )
            current_editor_ids = {e.id for e in current_editors}
            current_viewer_ids = {v.id for v in current_viewers}
            for target_user_id in current_editor_ids | current_viewer_ids | new_editor_ids | new_viewer_ids:
                if target_user_id in new_editor_ids:
                    if target_user_id not in current_editor_ids:
                        await collection_operations.grant_collection_access(
                            session, user, auth_backend, target_user_id, db_collection, "editor"
                        )
                elif target_user_id in new_viewer_ids:
                    if target_user_id not in current_viewer_ids:
                        await collection_operations.grant_collection_access(
                            session, user, auth_backend, target_user_id, db_collection, "viewer"
                        )
                else:
                    await collection_operations.revoke_collection_access(
                        session, user, auth_backend, target_user_id, db_collection
                    )
            return result

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
