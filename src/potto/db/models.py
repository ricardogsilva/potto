from typing import (
    TypedDict,
)

import pydantic
import sqlalchemy
from pydantic import (
    ConfigDict,
    field_serializer,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import (
    Column,
    Field,
    SQLModel,
)


def serialize_localizable_field(value: dict[str, str], _info):
    """Serialize a localizable field.

    Localizable fields use a JSONB type, which is not serialized by default, hence
    the need for this function.
    """
    return value


def serialize_localizable_list_field(value: dict[str, list[str]], _info):
    """Serialize a localizable list field.

    Localizable fields use a JSONB type, which is not serialized by default, hence
    the need for this function.
    """
    return value


class CollectionResource(SQLModel, table=True):
    __table_args__ = (
        sqlalchemy.Index(
            "idx_collectionresource_name_gin",
            "title",
            postgresql_using="gin"
        ),
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int | None = Field(
        default=None,
        primary_key=True,
    )
    resource_identifier: str = Field(
        min_length=3,
        max_length=100,
        index=True,
    )
    title: dict[str, str] = Field(sa_column=Column(JSONB))
    description: dict[str, str] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    keywords: dict[str, list[str]] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))

    @field_serializer("title", "description")
    def _serialize_localizable(self, value: dict[str, str] | None, info) -> dict[str, str] | None:
        return serialize_localizable_field(value, info) if value is not None else None

    @field_serializer("keywords")
    def _serialize_localizable_list(
        self, value: dict[str, list[str]], info
    ) -> dict[str, list[str]]:
        return serialize_localizable_list_field(value, info) if value is not None else None
    # extents
    # providers
    # links
    # limits
