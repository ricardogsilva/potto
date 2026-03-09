import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import User
from .common import _get_total_num_records


async def collect_all_users(
        session: AsyncSession,
) -> list[User]:
    statement = select(User).order_by(User.username)
    return list((await session.exec(statement)).all())


async def paginated_list_users(
        session: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        include_total: bool = False,
) -> tuple[list[User], int | None]:
    statement = select(User).order_by(User.username)
    offset = page_size * (page - 1)
    items = (await session.exec(statement.offset(offset).limit(page_size))).all()
    num_total = (
        await _get_total_num_records(session, statement) if include_total else None
    )
    return items, num_total


async def get_user(
        session: AsyncSession,
        user_id: uuid.UUID,
) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_username(
        session: AsyncSession,
        username: str,
) -> User | None:
    statement = select(User).where(User.username == username)
    return (await session.exec(statement)).first()
