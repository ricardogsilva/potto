import logging

from sqlmodel.ext.asyncio.session import AsyncSession

from ...exceptions import PottoException
from ...schemas.metadata import (
    LicenseInformation,
    DataProviderInformation,
    PointOfContact,
    ServerMetadataCreate,
    ServerMetadataFlattenedUpdate,
    ServerMetadataUpdate,
)
from ..models import ServerMetadata
from ..queries import get_metadata

logger = logging.getLogger(__name__)


async def create_metadata(
        session: AsyncSession, to_create: ServerMetadataCreate
) -> ServerMetadata:
    instance = ServerMetadata(**to_create.model_dump())
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return await get_metadata(session)


async def update_metadata(
        session: AsyncSession,
        db_metadata: ServerMetadata,
        to_update: ServerMetadataUpdate,
) -> ServerMetadata:
    for key, value in to_update.model_dump(exclude_unset=True).items():
        setattr(db_metadata, key, value)
    session.add(db_metadata)
    await session.commit()
    await session.refresh(db_metadata)
    return db_metadata


async def update_metadata_flattened(
        session: AsyncSession,
        db_metadata: ServerMetadata,
        to_update: ServerMetadataFlattenedUpdate
) -> ServerMetadata:
    unflattened_license = {}
    unflattened_data_provider = {}
    unflattened_point_of_contact = {}
    for key, value in to_update.model_dump(exclude_unset=True).items():
        if "data_license" in key:
            unflattened_license[key.replace("data_license_", "")] = value
        elif "data_provider" in key:
            unflattened_data_provider[key.replace("data_provider_", "")] = value
        elif "point_of_contact" in key:
            unflattened_point_of_contact[key.replace("point_of_contact_", "")] = value

    unflattened = ServerMetadataUpdate(
        title=to_update.title or db_metadata.title,
        description=to_update.description or db_metadata.description,
        keywords=to_update.keywords,
        license=LicenseInformation(
            name=unflattened_license.get("name", (db_metadata.license or {}).get("name")),
            url=unflattened_license.get("url", (db_metadata.license or {}).get("url")),
        ) if unflattened_license else None,
        data_provider=DataProviderInformation(
            name=unflattened_data_provider.get("name", (db_metadata.data_provider or {}).get("name")),
            url=unflattened_data_provider.get("url", (db_metadata.data_provider or {}).get("url")),
        ) if unflattened_data_provider else None,
        point_of_contact=PointOfContact(
            name=unflattened_point_of_contact.get("name", (db_metadata.point_of_contact or {}).get("name")),
            position=unflattened_point_of_contact.get("position", (db_metadata.point_of_contact or {}).get("position")),
            address=unflattened_point_of_contact.get("address", (db_metadata.point_of_contact or {}).get("address")),
            city=unflattened_point_of_contact.get("city", (db_metadata.point_of_contact or {}).get("city")),
            state_or_province=unflattened_point_of_contact.get("state_or_province", (db_metadata.point_of_contact or {}).get("state_or_province")),
            postal_code=unflattened_point_of_contact.get("postal_code", (db_metadata.point_of_contact or {}).get("postal_code")),
            country=unflattened_point_of_contact.get("country", (db_metadata.point_of_contact or {}).get("country")),
            phone=unflattened_point_of_contact.get("phone", (db_metadata.point_of_contact or {}).get("phone")),
            fax=unflattened_point_of_contact.get("fax", (db_metadata.point_of_contact or {}).get("fax")),
            email=unflattened_point_of_contact.get("email", (db_metadata.point_of_contact or {}).get("email")),
            url=unflattened_point_of_contact.get("url", (db_metadata.point_of_contact or {}).get("url")),
            contact_hours=unflattened_point_of_contact.get("contact_hours", (db_metadata.point_of_contact or {}).get("contact_hours")),
            contact_instructions=unflattened_point_of_contact.get("contact_instructions", (db_metadata.point_of_contact or {}).get("contact_instructions")),
        ) if unflattened_point_of_contact else None
    )
    return await update_metadata(session, db_metadata, unflattened)



async def delete_metadata(
        session: AsyncSession,
) -> None:
    if instance := (await get_metadata(session)):
        await session.delete(instance)
        await session.commit()
    else:
        raise PottoException(f"Server metadata not found.")