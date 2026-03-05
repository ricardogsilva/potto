import os
import re

import shapely
from sqlmodel.ext.asyncio.session import AsyncSession

from ..config import PottoSettings
from ..db.models import (
    CollectionItem,
    CollectionType,
)
from ..db.queries import paginated_list_collections
from .metadata import get_server_metadata


async def get_pygeoapi_config(
        session: AsyncSession,
        languages: list[str],
        public_url: str,
        *,
        collection_types: list[CollectionType] | None = None,
        resource_page: int = 1,
        resource_page_size: int | None = None,
        debug: bool = False,
) -> dict:
    metadata = await get_server_metadata(session)
    server_conf = metadata.get("server", {})
    server_map = server_conf.get("map", {})
    server_limits_conf = server_conf.get("limits", {})

    pygeoapi_config = {
        "server": {
            "admin": server_conf.get("admin", False),  # we don't use pygeoapi's admin, but rather provide our own
            "languages": languages,
            "limits": {
                "default_items": server_limits_conf.get("default_items", 20),
                "max_items": server_limits_conf.get("max_items", 50),
            },
            "map": {
                "url": server_map.get(
                    "map", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
                "attribution": server_map.get(
                    "attribution",
                    '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap contributors</a>'
                ),
            },
            "locale_dir": server_conf.get("locale_dir"),
            "url": public_url,
        },
        "logging": {
            "level": "DEBUG" if debug else "WARNING"
        },
        "metadata": {
            "identification": {
                "title": metadata.title,
                "description": metadata.description or "",
                "keywords": metadata.keywords or ["geospatial", "data", "api"],
                "keywords_type": None,
                "terms_of_service": None,
                "url": None,
            },
            "license": {
                "name": metadata.license.get("name", "Unknown"),
                "url": metadata.license.get("url"),
            },
            "provider": {
                "name": metadata.data_provider.get("name", "Organization Name"),
                "url": metadata.data_provider.get("url"),
            },
            "contact": {
                "name": metadata.point_of_contact.get("name", "Lastname, Firstname"),
                "position": metadata.point_of_contact.get("position", "Position Title"),
                "address": metadata.point_of_contact.get("address", "Mailing Address"),
                "city": metadata.point_of_contact.get("city", "City"),
                "stateorprovince": metadata.point_of_contact.get("stateorprovince", "Administrative Area"),
                "postalcode": metadata.point_of_contact.get("postalcode", "Zip or Postal Code"),
                "country": metadata.point_of_contact.get("country", "Country"),
                "phone": metadata.point_of_contact.get("phone", "+xx-xxx-xxx-xxxx"),
                "fax": metadata.point_of_contact.get("fax", "+xx-xxx-xxx-xxxx"),
                "email": metadata.point_of_contact.get("email", "you@example.org"),
                "url": metadata.point_of_contact.get("url", "Contact URL"),
                "hours": metadata.point_of_contact.get("hours", "Mo-Fr 08:00-17:00"),
                "instructions": metadata.point_of_contact.get("instructions", "During hours of service. Off on weekends."),
                "role": metadata.point_of_contact.get("role", "pointOfContact"),
            },
        },
        "resources": {}
    }

    # TODO: need to surface the total number of resources
    # TODO: this does not show other resources than collections
    collections, num_total = await paginated_list_collections(
        session,
        collection_type_filter=collection_types,
        page=resource_page,
        page_size=resource_page_size,
    )
    for db_collection in collections:
        pygeoapi_config["resources"][db_collection.resource_identifier] = (
            _convert_collection_to_pygeoapi_resource(db_collection)
        )
    # TODO: validate the config
    return pygeoapi_config


def _convert_collection_to_pygeoapi_resource(collection: CollectionItem) -> dict:
    links = []
    for collection_link in collection.additional_links or []:
        link_ = dict(collection_link)
        type_ = link_.pop("media_type", "")
        links.append(
            {
                "type": type_,
                **link_
            }
        )
    providers = []
    for provider in collection.providers or []:
        raw_data_value = provider.pop("data", "")
        interpolated_data_value = re.sub(
            r"\${?(\w+)}?",
            lambda re_match: os.getenv(re_match.group(1), "ENV_VAR_NOT_FOUND"),
            raw_data_value,
        )
        provider["data"] = interpolated_data_value
        providers.append(provider)

    return {
        "type": "collection",
        "title": collection.title,
        "description": collection.description or "",
        "keywords": collection.keywords or [],
        "linked-data": None,
        "links": links,
        "extents": {
            "spatial": {
                "bbox": (
                    collection.spatial_extent.bounds
                    if collection.spatial_extent
                    else shapely.box(-180, -90, 180, 90).bounds
                ),
                "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84",
            },
            "temporal": {
                "begin": (
                    collection.temporal_extent_begin.isoformat()
                    if collection.temporal_extent_begin else None
                ),
                "end": (
                    collection.temporal_extent_end.isoformat()
                    if collection.temporal_extent_end else None
                ),
            }
        },
        "providers": providers,
    }
