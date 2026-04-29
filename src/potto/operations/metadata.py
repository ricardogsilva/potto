from sqlmodel.ext.asyncio.session import AsyncSession

from ..authz.base import AuthorizationBackendProtocol
from ..db.queries import get_metadata
from ..db.models import ServerMetadata
from ..exceptions import PottoCannotEditServerMetadataException
from ..schemas.auth import PottoUser
from ..schemas.metadata import (
    ServerMetadataCreate,
    ServerMetadataUpdate,
)
from ..db.commands import metadata as metadata_commands


async def get_server_metadata(session: AsyncSession) -> ServerMetadata:
    """Return pre-existing server metadata or create if needed"""
    if existing := await get_metadata(session):
        return existing

    return await metadata_commands.create_metadata(
        session, ServerMetadataCreate(title="Default title")
    )


async def update_server_metadata(
    session: AsyncSession,
    user: PottoUser | None,
    authorization_backend: AuthorizationBackendProtocol,
    to_update: ServerMetadataUpdate,
) -> ServerMetadata:
    if not await authorization_backend.can_edit_server_metadata(user):
        raise PottoCannotEditServerMetadataException(
            "User does not have permission to edit server metadata."
        )
    db_metadata = await get_server_metadata(session)
    return await metadata_commands.update_metadata(session, db_metadata, to_update)
