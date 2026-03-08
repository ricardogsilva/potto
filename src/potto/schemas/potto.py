"""Schemas used for responses of the Potto wrapper."""

import dataclasses
import datetime as dt

from . import (
    base,
    items,
    metadata,
)
from . import pygeoapi_config
from .web.items import (
    FeatureFilter,
    ItemFilter,
)
from ..db import models


@dataclasses.dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int
    total: int


@dataclasses.dataclass(frozen=True)
class Collection:
    type_: base.CollectionType
    identifier: str
    title: base.Title
    description: base.MaybeDescription = None
    keywords: base.MaybeKeywords = None
    spatial_extent: base.MaybeShapelyGeometry = None
    temporal_extent_begin: dt.datetime | None = None
    temporal_extent_end: dt.datetime | None = None
    additional_links: list[dict[str, str | dict[str, str]]] | None = None
    providers: dict[str, base.CollectionProvider] | None = None


@dataclasses.dataclass(frozen=True)
class CollectionList:
    collections: list[Collection]
    pagination: Pagination


@dataclasses.dataclass(frozen=True)
class ServerMetadata:
    title: base.Title
    description: base.MaybeDescription = None
    keywords: base.MaybeKeywords = None
    keywords_type: str | None = None
    terms_of_service: base.MaybeDescription = None
    url: str | None = None
    license: metadata.LicenseInformation | None = None
    data_provider: metadata.DataProviderInformation | None = None
    point_of_contact: metadata.PointOfContact | None = None


@dataclasses.dataclass(frozen=True)
class PottoResponse:
    content_type: str
    content: dict | bytes
    metadata: dict [str, str] | None = None


@dataclasses.dataclass(frozen=True)
class LandingPage:
    metadata: models.ServerMetadata
    num_collections: int
    attribution: str | None = None
    collections: list[models.Collection] | None = None


@dataclasses.dataclass(frozen=True)
class ConformanceDetail:
    conforms_to: list[str]


@dataclasses.dataclass(frozen=True)
class FeatureListResponse:
    collection: models.Collection
    features: list[items.Feature]
    pagination: base.PaginationContext
    filter_: FeatureFilter | None = None
    metadata: dict [str, str] | None = None


@dataclasses.dataclass(frozen=True)
class FeatureResponse:
    collection: models.Collection
    feature: items.Feature
    metadata: dict [str, str] | None = None
