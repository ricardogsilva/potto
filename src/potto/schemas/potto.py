"""Schemas used for responses of the Potto wrapper."""

import dataclasses
import datetime as dt
import json
import shapely

from . import (
    base,
    metadata,
    pygeoapi_config,
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
class Feature:

    id_: str
    properties: dict[str, str | int | float | bool]
    geometry: shapely.Geometry

    @classmethod
    def from_pygeoapi_feature(cls, pygeoapi_feature: dict) -> "Feature":
        return cls(
            id=str(pygeoapi_feature["id"]),
            properties={k: v for k, v in pygeoapi_feature["properties"].items() if k != "id"},
            geometry=shapely.from_geojson(json.dumps(pygeoapi_feature["geometry"]))
        )


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
    collections: CollectionList
    attribution: str | None = None


@dataclasses.dataclass(frozen=True)
class ConformanceDetail:
    conforms_to: list[str]


@dataclasses.dataclass(frozen=True)
class FeatureListResponse:
    collection: models.Collection
    features: list[Feature]
    pagination: base.PaginationContext
    filter_: base.FeatureFilter | None = None
    metadata: dict [str, str] | None = None


@dataclasses.dataclass(frozen=True)
class FeatureResponse:
    collection: Collection
    feature: Feature
    metadata: dict [str, str] | None = None
