import datetime as dt
import logging
from typing import (
    Annotated,
    Any,
)

import shapely
import sqlalchemy
from geoalchemy2 import (
    Geometry,
    WKBElement,
)
from geoalchemy2.shape import to_shape
from pydantic import (
    BeforeValidator,
    ConfigDict,
    field_serializer,
    PlainSerializer,
)

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import (
    Column,
    Field,
    Relationship,
    SQLModel,
)

logger = logging.getLogger(__name__)


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


class ShapelyGeometryAdapter(Geometry):
    """Geometry column type that converts to/from shapely objects transparently.

    geoalchemy2's bind_processor passes unrecognised types through as-is,
    causing psycopg3 to fail on raw shapely objects. This subclass intercepts
    both directions: shapely → EWKT string on writes, WKBElement → shapely on reads.
    """

    def bind_processor(self, dialect):
        parent = super().bind_processor(dialect)

        def process(value):
            if isinstance(value, shapely.Geometry):
                return f"SRID={self.srid};{shapely.to_wkt(value)}"
            return parent(value)

        return process

    def result_processor(self, dialect, coltype):
        parent = super().result_processor(dialect, coltype)

        def process(value):
            if parent is not None:
                value = parent(value)
            return to_shape(value) if value is not None else None

        return process


def to_shapely(
        value: str | WKBElement | shapely.Geometry | None
) -> shapely.Geometry | None:
    if not value:
        return None
    elif isinstance(value, shapely.Geometry):
        return value
    elif isinstance(value, str):
        return shapely.from_wkt(value)
    else:
        return to_shape(value)


ShapelyGeometry = Annotated[
    shapely.Geometry | None,
    BeforeValidator(to_shapely),
    PlainSerializer(
        lambda geom: shapely.to_geojson(geom) if geom else None,
        return_type=str
    ),
]


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
    title: dict[str, str] | str = Field(sa_column=Column(JSONB))
    description: dict[str, str] | str | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True))
    keywords: dict[str, list[str]] | list[str] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True))
    spatial_extent: ShapelyGeometry = Field(
        default=None,
        sa_column=Column(
            ShapelyGeometryAdapter(),
            nullable=True
        )
    )
    temporal_extent_begin: dt.datetime | None = None
    temporal_extent_end: dt.datetime | None = None
    providers: list[dict[str, Any]] = Field(sa_column=Column(JSONB, nullable=True))
    additional_links: list[dict[str, str | dict[str, str]]] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True))


    @field_serializer("title", "description")
    def _serialize_localizable(self, value: dict[str, str] | None, info) -> dict[str, str] | None:
        return serialize_localizable_field(value, info) if value is not None else None

    @field_serializer("keywords")
    def _serialize_localizable_list(
        self, value: dict[str, list[str]], info
    ) -> dict[str, list[str]]:
        return serialize_localizable_list_field(value, info) if value is not None else None

