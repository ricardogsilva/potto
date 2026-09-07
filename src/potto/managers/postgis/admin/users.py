from typing import (
    Any,
    cast,
    TYPE_CHECKING,
)

import pydantic
from starlette.requests import Request
from starlette_admin.fields import PasswordField

from ....exceptions import PottoException
from ....schemas.auth import (
    PottoUser,
    UserCreate,
    UserUpdate,
)
from ....webapp.admin.views import _PottoAdminModelView
from ..db.models import User

if TYPE_CHECKING:
    from ....config import PottoSettings


class UserView(_PottoAdminModelView):
    """Custom starlette-admin view for managing local users.

    This view overrides both the `create` and `edit` methods in order to ensure they
    use our own manager, thus ensuring a consistent schema is preserved whether
    modifications are done via the admin UI, the web API or the CLI.

    User creation is restricted to admins and only available when using the local
    authorization backend (not supported with OPA).
    """

    async def async_can_create(self, request: Request) -> bool:
        user = cast(PottoUser, request.user)
        settings = cast("PottoSettings", request.app.state.SETTINGS)
        return await settings.get_authorization_backend().can_create_user(user)

    fields = (
        User.id,
        User.username,
        User.email,
        PasswordField("password"),
        User.is_active,
        User.scopes,
    )
    exclude_fields_from_detail = ("password", "id")
    # "id" must stay visible in the list view: starlette-admin's order_by
    # validation requires the default sort field (pk_attr) to be both sortable
    # and NOT excluded from the list, which the select2 pickers used by
    # CollectionView's owner/editors/viewers fields rely on.
    exclude_fields_from_list = ("password",)
    exclude_fields_from_create = ("id",)
    exclude_fields_from_edit = ("id",)

    async def create(self, request: Request, data: dict[str, Any]) -> Any:
        user = cast(PottoUser, request.user)
        settings = cast("PottoSettings", request.app.state.SETTINGS)
        user_account_manager = settings.get_user_account_manager()
        try:
            return await user_account_manager.create_user(
                UserCreate(
                    **{
                        k: v
                        for k, v in {
                            "username": data["username"],
                            "is_active": data["is_active"],
                            "email": data["email"] or None,
                            "scopes": data["scopes"] or None,
                            "password": data["password"],
                        }.items()
                        if v is not None
                    }
                ),
                requesting_user=user,
            )
        except pydantic.ValidationError as err:
            self.handle_exception(err)
        except PottoException as err:
            self.handle_exception(err)

    async def edit(self, request: Request, pk: Any, data: dict[str, Any]) -> Any:
        user = cast(PottoUser, request.user)
        settings = cast("PottoSettings", request.app.state.SETTINGS)
        user_account_manager = settings.get_user_account_manager()
        try:
            return await user_account_manager.update_user(
                pk,
                UserUpdate(
                    **{
                        k: v
                        for k, v in {
                            "username": data["username"],
                            "is_active": data["is_active"],
                            "email": data["email"] or None,
                            "scopes": data["scopes"] or None,
                            "password": data["password"] or None,
                        }.items()
                        if v is not None
                    }
                ),
                requesting_user=user,
            )
        except pydantic.ValidationError as err:
            return self.handle_exception(err)
        except PottoException as err:
            self.handle_exception(err)
