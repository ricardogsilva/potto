import logging
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from ...exceptions import PottoException
from ...schemas.collections import (
    CollectionCreate,
    CollectionUpdate
)
from ..models import (
    Collection,
    User,
)
from ..queries import get_collection

logger = logging.getLogger(__name__)


async def _verify_owner_exists(session: AsyncSession, owner_id: uuid.UUID) -> None:
    if not await session.get(User, owner_id):
        raise PottoException(f"User with id {owner_id} does not exist.")


async def create_collection(
        session: AsyncSession, to_create: CollectionCreate
) -> Collection:
    await _verify_owner_exists(session, to_create.owner_id)
    instance = Collection(**to_create.model_dump())
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return await get_collection(session, instance.id)


async def update_collection(
        session: AsyncSession,
        db_collection: Collection,
        to_update: CollectionUpdate,
) -> Collection:
    updates = to_update.model_dump(exclude_unset=True)
    if "owner_id" in updates:
        await _verify_owner_exists(session, updates["owner_id"])
    for key, value in updates.items():
        setattr(db_collection, key, value)
    session.add(db_collection)
    await session.commit()
    await session.refresh(db_collection)
    return db_collection


async def delete_collection(
        session: AsyncSession,
        collection_id: int,
) -> None:
    if instance := (await get_collection(session, collection_id)):
        await session.delete(instance)
        await session.commit()
    else:
        raise PottoException(f"Collection with id {collection_id} does not exist.")
