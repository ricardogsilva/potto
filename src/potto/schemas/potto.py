import dataclasses

from . import items
from . import pygeoapi_config


@dataclasses.dataclass(frozen=True)
class PottoResponse:
    content_type: str
    content: dict | bytes
    metadata: dict [str, str] | None = None


@dataclasses.dataclass(frozen=True)
class CollectionFeatureListResponse:
    resource: pygeoapi_config.ItemCollectionConfig
    provider: pygeoapi_config.ProviderConfig
    features: list[items.Feature]
    pagination: items.FeatureCollectionPaginationContext
    filter_: items.FeatureCollectionFilter | None = None
    metadata: dict [str, str] | None = None


@dataclasses.dataclass(frozen=True)
class FeatureResponse:
    resource: pygeoapi_config.ItemCollectionConfig
    provider: pygeoapi_config.ProviderConfig
    feature: items.Feature
    metadata: dict [str, str] | None = None
