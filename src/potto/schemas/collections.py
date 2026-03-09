import datetime as dt
import logging
import uuid

import pydantic

from .base import (
    CollectionProvider,
    CollectionType,
    MaybeDescription,
    Extent,
    MaybeKeywords,
    MaybeShapelyGeometry,
    Title,
)

logger = logging.getLogger(__name__)


class CollectionCreate(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)
    resource_identifier: str = pydantic.Field(min_length=3, max_length=100)
    owner_id: uuid.UUID
    collection_type: CollectionType
    title: Title
    description: MaybeDescription = None
    keywords: MaybeKeywords = None
    spatial_extent: MaybeShapelyGeometry = None
    temporal_extent_begin: dt.datetime | None = None
    temporal_extent_end: dt.datetime | None = None
    additional_links: list[dict[str, str | dict[str, str]]] | None = None
    providers: dict[str, CollectionProvider] | None = None


class CollectionUpdate(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)
    owner_id: uuid.UUID | None = None
    collection_type: CollectionType | None = None
    title: Title | None = None
    description: MaybeDescription = None
    keywords: MaybeKeywords = None
    spatial_extent: MaybeShapelyGeometry = None
    temporal_extent_begin: dt.datetime | None = None
    temporal_extent_end: dt.datetime | None = None
    additional_links: list[dict[str, str | dict[str, str]]] | None = None
    providers: dict[str, CollectionProvider] | None = None
