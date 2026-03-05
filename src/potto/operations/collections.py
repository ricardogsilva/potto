import logging
import datetime as dt
import shapely
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db.models import (
    CollectionItem,
    CollectionType,
)
from ..db.commands import (
    create_collection,
    update_collection,
)
from ..db.queries import get_collection_by_resource_identifier
from ..exceptions import PottoException
from ..schemas.collections import (
    CollectionItemCreate,
    CollectionItemUpdate,
)

logger = logging.getLogger(__name__)


async def import_pygeoapi_collection(
        session: AsyncSession,
        identifier: str,
        resource: list[dict],
        *,
        overwrite: bool = False,
) -> CollectionItem:
    existing_db_collection = await get_collection_by_resource_identifier(session, identifier)
    if existing_db_collection and not overwrite:
        raise PottoException(f"Collection {identifier!r} already exists!")
    logger.debug(f"About to import resource {resource=}")
    if resource.get("type") != "collection":
        raise PottoException("pygeoapi resource is not a collection type")
    provider_types = set([p.get("type") for p in resource.get("providers", [])])
    collection_type_mapping = {
        "feature": CollectionType.FEATURE_COLLECTION,
        "record": CollectionType.RECORD_COLLECTION,
        "coverage": CollectionType.COVERAGE,
        # mapping provider 'map' to 'CollectionType.COVERAGE' is really an arbitrary mapping,
        # pygeoapi does not seem to know about the underlying type of data of a map
        "map": CollectionType.COVERAGE,
    }
    try:
        collection_type = collection_type_mapping[
            provider_types.intersection(set(collection_type_mapping)).pop()
        ]
    except (TypeError, KeyError) as err:
        raise PottoException(f"Unsupported collection type: {provider_types=}") from err

    resource_spatial_extents = resource.get("extents", {}).get("spatial", {})
    try:
        # TODO: support inspecting the CRS
        spatial_extent = shapely.box(*resource_spatial_extents.get("bbox"))
    except TypeError:
        spatial_extent = None
    providers = {}
    for prov in resource.get("providers", []):
        type_ = prov.get("type")
        if providers.get(type_) is None:
            providers[type_] = prov
        else:
            continue

    if existing_db_collection and overwrite:
        logger.debug(f"Updating existing collection {identifier!r}...")
        to_update = CollectionItemUpdate(
            collection_type=collection_type,
            title=resource.get("title", ""),
            description=resource.get("description"),
            keywords=resource.get("keywords"),
            spatial_extent=spatial_extent,
            temporal_extent_begin=resource.get("extents", {}).get("temporal", {}).get("begin"),
            temporal_extent_end=resource.get("extents", {}).get("temporal", {}).get("end"),
            additional_links=resource.get("links"),
            providers=providers
        )
        return await update_collection(session, existing_db_collection, to_update)
    else:
        to_create = CollectionItemCreate(
            resource_identifier=identifier,
            collection_type=collection_type,
            title=resource.get("title", ""),
            description=resource.get("description"),
            keywords=resource.get("keywords"),
            spatial_extent=spatial_extent,
            temporal_extent_begin=resource.get("extents", {}).get("temporal", {}).get("begin"),
            temporal_extent_end=resource.get("extents", {}).get("temporal", {}).get("end"),
            additional_links=resource.get("links"),
            providers=providers
        )
        return await create_collection(session, to_create)
