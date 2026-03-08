"""Internal schemas used for responses of the Potto wrapper."""

import dataclasses

from . import (
    base,
    items,
)
from . import pygeoapi_config
from .web.items import (
    FeatureFilter,
    ItemFilter,
)
from ..db import models


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
