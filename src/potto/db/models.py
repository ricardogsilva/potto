import datetime as dt
import logging
from typing import Any

import pydantic
import shapely
import sqlalchemy
import geoalchemy2
from geoalchemy2.shape import to_shape

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import (
    Field,
    SQLModel,
)

from ..schemas.base import (
    CollectionProvider,
    CollectionType,
    Title,
    MaybeDescription,
    MaybeKeywords,
    MaybeShapelyGeometry,
)

logger = logging.getLogger(__name__)


class ShapelyGeometryAdapter(geoalchemy2.Geometry):
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


class Collection(SQLModel, table=True):
    __table_args__ = (
        sqlalchemy.Index(
            "idx_collection_title_gin",
            "title",
            postgresql_using="gin"
        ),
    )

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

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
    description: MaybeDescription = Field(default=None, sa_type=JSONB(), nullable=True)
    keywords: MaybeKeywords = Field(default=None, sa_type=JSONB(), nullable=True)
    spatial_extent: MaybeShapelyGeometry = Field(
        default=None,
        sa_type=ShapelyGeometryAdapter(),
        nullable=True,
    )
    temporal_extent_begin: dt.datetime | None = None
    temporal_extent_end: dt.datetime | None = None
    additional_links: list[dict[str, str | dict[str, str]]] | None = Field(
        default=None, sa_type=JSONB(), nullable=True)
    providers: dict[str, CollectionProvider] | None = Field(
        default=None,
        sa_type=JSONB(),
        nullable=True
    )


class ServerMetadata(SQLModel, table=True):
    id: int | None = Field(
        default=None,
        primary_key=True,
    )
    title: Title = Field(sa_type=JSONB())
    description: MaybeDescription = Field(default=None, sa_type=JSONB(), nullable=True)
    keywords: MaybeKeywords = Field(default=None, sa_type=JSONB(), nullable=True)
    keywords_type: str | None = Field(default=None, min_length=3, max_length=50, nullable=True)
    terms_of_service: MaybeDescription = Field(default=None, sa_type=JSONB(), nullable=True)
    url: str | None = Field(default=None, min_length=3, max_length=100, nullable=True)
    license: dict[str, Any] = Field(default=None, sa_type=JSONB(), nullable=True)
    data_provider: dict[str, Any] = Field(default=None, sa_type=JSONB(), nullable=True)
    point_of_contact: dict[str, Any] = Field(default=None, sa_type=JSONB(), nullable=True)
