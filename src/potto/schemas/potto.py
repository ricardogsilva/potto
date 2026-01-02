"""Internal schemas used for potto responses."""

import dataclasses

from . import collections as collections_schemas
from . import pygeoapi_config


@dataclasses.dataclass(frozen=True)
class PottoResponse:
    content_type: str
    content: dict | bytes
    metadata: dict [str, str] | None = None


@dataclasses.dataclass(frozen=True)
class LandingPage:
    title: str | None = None
    description: str | None = None
    attribution: str | None = None
    collections: list[collections_schemas.Collection] | None = None


@dataclasses.dataclass(frozen=True)
class ConformanceDetail:
    conforms_to: list[str]


@dataclasses.dataclass(frozen=True)
class CollectionList:
    collections: list[collections_schemas.Collection]
    pagination: collections_schemas.CollectionItemsPaginationContext
    filter_: collections_schemas.ItemFilter | None = None
    metadata: dict [str, str] | None = None


@dataclasses.dataclass(frozen=True)
class CollectionDetail:
    collection: collections_schemas.Collection
    resource: pygeoapi_config.ItemCollectionConfig
    metadata: dict [str, str] | None = None


@dataclasses.dataclass(frozen=True)
class CollectionFeatureListResponse:
    resource: pygeoapi_config.ItemCollectionConfig
    provider: pygeoapi_config.ProviderConfig
    features: list[collections_schemas.Feature]
    pagination: collections_schemas.CollectionItemsPaginationContext
    filter_: collections_schemas.FeatureFilter | None = None
    metadata: dict [str, str] | None = None


@dataclasses.dataclass(frozen=True)
class FeatureResponse:
    resource: pygeoapi_config.ItemCollectionConfig
    provider: pygeoapi_config.ProviderConfig
    feature: collections_schemas.Feature
    metadata: dict [str, str] | None = None
