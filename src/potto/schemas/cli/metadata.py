import pydantic

from ..base import (
    Title,
    MaybeDescription,
    MaybeKeywords,
)
from ..metadata import ServerMetadata


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
    def from_potto(cls, item: ServerMetadata) -> "ServerMetadataDetail":
        data_license = item.license
        data_provider = item.data_provider
        point_of_contact = item.point_of_contact
        return cls(
            title=item.title,
            description=item.description,
            keywords=item.keywords,
            keywords_type=item.keywords_type,
            terms_of_service=item.terms_of_service,
            url=item.url,
            license_name=data_license.name if data_license else None,
            license_url=data_license.url if data_license else None,
            data_provider_name=data_provider.name if data_provider else None,
            data_provider_url=data_provider.url if data_provider else None,
            point_of_contact_name=point_of_contact.name if point_of_contact else None,
            point_of_contact_position=point_of_contact.position
            if point_of_contact
            else None,
            point_of_contact_address=point_of_contact.address
            if point_of_contact
            else None,
            point_of_contact_city=point_of_contact.city if point_of_contact else None,
            point_of_contact_state_or_province=(
                point_of_contact.state_or_province if point_of_contact else None
            ),
            point_of_contact_postal_code=(
                point_of_contact.postal_code if point_of_contact else None
            ),
            point_of_contact_country=point_of_contact.country
            if point_of_contact
            else None,
            point_of_contact_phone=point_of_contact.phone if point_of_contact else None,
            point_of_contact_fax=point_of_contact.fax if point_of_contact else None,
            point_of_contact_email=point_of_contact.email if point_of_contact else None,
            point_of_contact_url=point_of_contact.url if point_of_contact else None,
            point_of_contact_contact_hours=(
                point_of_contact.contact_hours if point_of_contact else None
            ),
            point_of_contact_contact_instructions=(
                point_of_contact.contact_instructions if point_of_contact else None
            ),
        )
