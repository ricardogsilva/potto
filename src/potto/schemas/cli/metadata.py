import pydantic

from ...db.models import (
    ServerMetadata,
)
from ..base import (
    Title,
    MaybeDescription,
    MaybeKeywords,
)


class ServerMetadataDetail(pydantic.BaseModel):
    title: Title
    description: MaybeDescription
    keywords: MaybeKeywords
    keywords_type: str | None
    terms_of_service: MaybeDescription
    url: str | None
    license_name: str | None
    license_url: str | None
    data_provider_name: str | None
    data_provider_url: str | None
    point_of_contact_name: str | None
    point_of_contact_position: str | None
    point_of_contact_address: str | None
    point_of_contact_city: str | None
    point_of_contact_state_or_province: str | None
    point_of_contact_postal_code: str | None
    point_of_contact_country: str | None
    point_of_contact_phone: str | None
    point_of_contact_fax: str | None
    point_of_contact_email: str | None
    point_of_contact_url: str | None
    point_of_contact_contact_hours: str | None
    point_of_contact_contact_instructions: str | None

    @classmethod
    def from_db_item(cls, item: ServerMetadata) ->"ServerMetadataDetail":
        data_license = item.license or {}
        data_provider = item.data_provider or {}
        point_of_contact = item.point_of_contact or {}
        return cls(
            title=item.title,
            description=item.description,
            keywords=item.keywords,
            keywords_type=item.keywords_type,
            terms_of_service=item.terms_of_service,
            url=item.url,
            license_name=data_license.get("name"),
            license_url=data_license.get("url"),
            data_provider_name=data_provider.get("name"),
            data_provider_url=data_provider.get("url"),
            point_of_contact_name=point_of_contact.get("name"),
            point_of_contact_position=point_of_contact.get("position"),
            point_of_contact_address=point_of_contact.get("address"),
            point_of_contact_city=point_of_contact.get("city"),
            point_of_contact_state_or_province=point_of_contact.get("state_or_province"),
            point_of_contact_postal_code=point_of_contact.get("postal_code"),
            point_of_contact_country=point_of_contact.get("country"),
            point_of_contact_phone=point_of_contact.get("phone"),
            point_of_contact_fax=point_of_contact.get("fax"),
            point_of_contact_email=point_of_contact.get("email"),
            point_of_contact_url=point_of_contact.get("url"),
            point_of_contact_contact_hours=point_of_contact.get("contact_hours"),
            point_of_contact_contact_instructions=point_of_contact.get("contact_instructions"),
        )


