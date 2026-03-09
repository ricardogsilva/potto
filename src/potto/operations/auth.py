import logging
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.authentication import BaseUser

from ..db.commands import auth as auth_commands
from ..db.queries import auth as auth_queries
from ..db.models import User
from ..schemas.auth import (
    UserCreate,
    UserUpdate,
)

logger = logging.getLogger(__name__)


async def create_user(
        session: AsyncSession,
        user: BaseUser,
        to_create: UserCreate,
) -> User:
    # TODO: check user permissions
    return await auth_commands.create_user(session, to_create)


async def update_user(
        session: AsyncSession,
        user: BaseUser,
        db_user: User,
        to_update: UserUpdate,
) -> User:
    # TODO: check user permissions
    return await auth_commands.update_user(session, db_user, to_update)


async def delete_user(
        session: AsyncSession,
        user: BaseUser,
        user_id: uuid.UUID,
) -> None:
    # TODO: check user permissions
    return await auth_commands.delete_user(session, user_id)


async def paginated_list_users(
        session: AsyncSession,
        user: BaseUser,
        *,
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
    )


async def get_user(
        session: AsyncSession,
        user: BaseUser,
        user_id: uuid.UUID,
) -> User | None:
    # TODO: check user permissions
    return await auth_queries.get_user(session, user_id)
