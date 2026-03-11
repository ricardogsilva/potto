import logging

from .schemas.base import CollectionType
from .exceptions import PottoException

logger = logging.getLogger(__name__)


def get_collection_type(pygeoapi_collection: dict) -> CollectionType:
    provider_types = set(
        [p.get("type") for p in pygeoapi_collection.get("providers", [])]
    )
    collection_type_mapping = {
        "feature": CollectionType.FEATURE_COLLECTION,
        "record": CollectionType.RECORD_COLLECTION,
        "coverage": CollectionType.COVERAGE,
        # mapping provider 'map' to 'CollectionType.COVERAGE' is really an arbitrary mapping,
        # pygeoapi does not seem to know about the underlying type of data of a map
        "map": CollectionType.COVERAGE,
    }
    try:
        return collection_type_mapping[
            provider_types.intersection(set(collection_type_mapping)).pop()
        ]
    except (TypeError, KeyError) as err:
        raise PottoException(f"Unsupported collection type: {provider_types=}") from err
