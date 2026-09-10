from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import ServerMetadata


async def get_metadata(
    session: AsyncSession,
) -> ServerMetadata | None:
    statement = select(ServerMetadata)
    return (await session.exec(statement)).first()
