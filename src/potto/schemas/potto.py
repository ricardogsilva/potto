import dataclasses

from . import items
from . import pygeoapi_config


@dataclasses.dataclass(frozen=True)
class PottoResponse:
    content_type: str
    content: dict | bytes
    metadata: dict [str, str] | None = None


@dataclasses.dataclass(frozen=True)
class ResponseContext:
    resource: pygeoapi_config.ItemCollectionConfig  # | ProcessConfig | StacCollectionConfig
    provider: pygeoapi_config.ProviderConfig


@dataclasses.dataclass(frozen=True)
class PottoStructuredResponse:
    context: ResponseContext
    content: items.FeatureList
    metadata: dict [str, str] | None = None
