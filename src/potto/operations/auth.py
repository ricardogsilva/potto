import logging
import re

from sqlmodel.ext.asyncio.session import AsyncSession

from ..authz.base import AuthorizationBackendProtocol
from ..db.commands import auth as auth_commands
from ..db.queries import auth as auth_queries
from ..db.queries import collections as collection_queries
from ..db.models import User
from ..exceptions import (
    PottoCannotCreateUserException,
    PottoCannotSetAdminScopeException,
    PottoCannotSetScopesException,
)
from ..schemas.auth import (
    PottoScope,
    PottoUser,
    UserCreate,
    UserUpdate,
)

logger = logging.getLogger(__name__)

_EDITOR_SCOPE_RE = re.compile(r"^collection-(.+):editor$")


async def create_user(
        session: AsyncSession,
        requesting_user: PottoUser | None,
        authorization_backend: AuthorizationBackendProtocol,
        to_create: UserCreate,
) -> User:
    if not await authorization_backend.can_create_user(requesting_user):
        raise PottoCannotCreateUserException(
            "User does not have permission to create new users."
        )
    if to_create.scopes:
        await _check_scope_assignment(
            session, requesting_user, authorization_backend, to_create.scopes
        )
    return await auth_commands.create_user(session, to_create)


async def update_user(
        session: AsyncSession,
        requesting_user: PottoUser | None,
        authorization_backend: AuthorizationBackendProtocol,
        db_user: User,
        to_update: UserUpdate,
) -> User:
    if to_update.scopes is not None:
        await _check_scope_assignment(
            session, requesting_user, authorization_backend, to_update.scopes
        )
    return await auth_commands.update_user(session, db_user, to_update)


async def _check_scope_assignment(
        session: AsyncSession,
        requesting_user: PottoUser | None,
        authorization_backend: AuthorizationBackendProtocol,
        new_scopes: list[str],
) -> None:
    if PottoScope.ADMIN.value in new_scopes:
        if not await authorization_backend.can_assign_admin_scope(requesting_user):
            raise PottoCannotSetAdminScopeException(
                "User does not have permission to assign the admin scope."
            )
    editable_identifiers = await _get_editable_collection_identifiers(
        session, requesting_user
    )
    if not await authorization_backend.can_set_user_scopes(
        requesting_user, new_scopes, editable_identifiers
    ):
        raise PottoCannotSetScopesException(
            "User does not have permission to set these scopes."
        )


async def _get_editable_collection_identifiers(
        session: AsyncSession,
        user: PottoUser | None,
) -> list[str]:
    if user is None:
        return []
    owned = await collection_queries.get_owned_collection_identifiers(session, user.id)
    from_scopes = [
        m.group(1) for scope in user.scopes if (m := _EDITOR_SCOPE_RE.match(scope))
    ]
    return list({*owned, *from_scopes})


async def delete_user(
        session: AsyncSession,
        requesting_user: PottoUser | None,
        user_id: str,
) -> None:
    # TODO: check user permissions
    return await auth_commands.delete_user(session, user_id)


async def paginated_list_users(
        session: AsyncSession,
        *,
        admin_filter: bool = False,
        page: int = 1,
        page_size: int = 20,
        include_total: bool = False,
) -> tuple[list[User], int | None]:
    # TODO: check user permissions
    return await auth_queries.paginated_list_users(
        session,
        page=page,
        page_size=page_size,
        include_total=include_total,
        admin_filter=admin_filter,
    )


async def get_user(
        session: AsyncSession,
        user_id: str,
) -> User | None:
    # TODO: check user permissions
    return await auth_queries.get_user(session, user_id)
