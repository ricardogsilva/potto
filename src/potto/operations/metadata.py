from sqlmodel.ext.asyncio.session import AsyncSession

from ..db.queries import get_metadata
from ..db.models import PottoMetadata
from ..schemas.metadata import PottoMetadataCreate
from ..db.commands import create_metadata


async def get_server_metadata(session: AsyncSession) -> PottoMetadata:
    """Return pre-existing server metadata or create if needed"""
    if existing := await get_metadata(session):
        return existing

    return await create_metadata(
        session,
        PottoMetadataCreate(
            title="Default title"
        )
    )