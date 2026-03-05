import logging

from sqlmodel.ext.asyncio.session import AsyncSession

from ...exceptions import PottoException
from ...schemas.collections import (
    CollectionItemCreate,
    CollectionItemUpdate
)
from ..models import CollectionItem
from ..queries import (
    get_collection,
    get_collection_by_resource_identifier
)

logger = logging.getLogger(__name__)


async def create_collection(
        session: AsyncSession, to_create: CollectionItemCreate
) -> CollectionItem:
    instance = CollectionItem(**to_create.model_dump())
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return await get_collection(session, instance.id)


async def update_collection(
        session: AsyncSession,
        db_collection: CollectionItem,
        to_update: CollectionItemUpdate,
) -> CollectionItem:
    for key, value in to_update.model_dump(exclude_unset=True).items():
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
