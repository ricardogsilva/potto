from sqlmodel.ext.asyncio.session import AsyncSession

from ..db.queries import get_metadata
from ..db.models import ServerMetadata
from ..schemas.metadata import ServerMetadataCreate
from ..db.commands import metadata as metadata_commands


async def get_server_metadata(session: AsyncSession) -> ServerMetadata:
    """Return pre-existing server metadata or create if needed"""
    if existing := await get_metadata(session):
        return existing

    return await metadata_commands.create_metadata(
        session,
        ServerMetadataCreate(
            title="Default title"
        )
    )