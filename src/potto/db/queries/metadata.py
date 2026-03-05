from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import PottoMetadata


async def get_metadata(
        session: AsyncSession,
) -> PottoMetadata | None:
    statement = select(PottoMetadata)
    return (await session.exec(statement)).first()
