import datetime as dt
import enum
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
    BaseModel,
    BeforeValidator,
    ConfigDict,
    PlainSerializer,
)

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import (
    Field,
    SQLModel,
)

logger = logging.getLogger(__name__)


class CollectionType(str, enum.Enum):
    COVERAGE = "coverage"
    FEATURE_COLLECTION = "feature_collection"
    RECORD_COLLECTION = "record_collection"


def serialize_localizable_field(value: dict[str, str] | str, _info):
    """Serialize a localizable field.

    Localizable fields use a JSONB type, which is not serialized by default, hence
    the need for this function.
    """
    return value


def serialize_localizable_list_field(value: dict[str, list[str]] | list[str], _info):
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


MaybeShapelyGeometry = Annotated[
    shapely.Geometry | None,
    BeforeValidator(to_shapely),
    PlainSerializer(
        lambda geom: shapely.to_geojson(geom) if geom else None,
        return_type=str
    ),
]

Title = Annotated[
    dict[str, str] | str,
    PlainSerializer(serialize_localizable_field)
]
Description = Annotated[
    dict[str, str] | str | None,
    PlainSerializer(serialize_localizable_field)
]
Keywords = Annotated[
    dict[str, list[str]] | list[str] | None,
    PlainSerializer(serialize_localizable_list_field)
]


class CollectionItem(SQLModel, table=True):
    __table_args__ = (
        sqlalchemy.Index(
            "idx_collection_title_gin",
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
        unique=True,
    )
    collection_type: CollectionType
    title: Title = Field(sa_type=JSONB())
    description: Description = Field(default=None, sa_type=JSONB(), nullable=True)
    keywords: Keywords = Field(default=None, sa_type=JSONB(), nullable=True)
    spatial_extent: MaybeShapelyGeometry = Field(
        default=None,
        sa_type=ShapelyGeometryAdapter(),
        nullable=True,
    )
    temporal_extent_begin: dt.datetime | None = None
    temporal_extent_end: dt.datetime | None = None
    additional_links: list[dict[str, str | dict[str, str]]] | None = Field(
        default=None, sa_type=JSONB(), nullable=True)
    providers: dict[str, dict[str, Any]] | None = Field(default=None, sa_type=JSONB(), nullable=True)


class PottoMetadata(SQLModel, table=True):
    id: int | None = Field(
        default=None,
        primary_key=True,
    )
    title: Title = Field(sa_type=JSONB())
    description: Description = Field(default=None, sa_type=JSONB(), nullable=True)
    keywords: Keywords = Field(default=None, sa_type=JSONB(), nullable=True)
    license: dict[str, Any] = Field(default=None, sa_type=JSONB(), nullable=True)
    data_provider: dict[str, Any] = Field(default=None, sa_type=JSONB(), nullable=True)
    point_of_contact: dict[str, Any] = Field(default=None, sa_type=JSONB(), nullable=True)
