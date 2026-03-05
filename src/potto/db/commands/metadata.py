import logging

from sqlmodel.ext.asyncio.session import AsyncSession

from ...exceptions import PottoException
from ...schemas.metadata import (
    PottoMetadataCreate,
    PottoMetadataUpdate
)
from ..models import PottoMetadata
from ..queries import get_metadata

logger = logging.getLogger(__name__)


async def create_metadata(
        session: AsyncSession, to_create: PottoMetadataCreate
) -> PottoMetadata:
    instance = PottoMetadata(**to_create.model_dump())
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return await get_metadata(session)


async def update_metadata(
        session: AsyncSession,
        db_metadata: PottoMetadata,
        to_update: PottoMetadataUpdate,
) -> PottoMetadata:
    for key, value in to_update.model_dump(exclude_unset=True).items():
        setattr(db_metadata, key, value)
    session.add(db_metadata)
    await session.commit()
    await session.refresh(db_metadata)
    return db_metadata


async def delete_metadata(
        session: AsyncSession,
) -> None:
    if instance := (await get_metadata(session)):
        await session.delete(instance)
        await session.commit()
    else:
        raise PottoException(f"Server metadata not found.")
