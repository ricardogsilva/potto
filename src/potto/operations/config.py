import logging
import os
import re

import shapely
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db.models import (
    Collection,
    CollectionType,
)
from ..db.queries import paginated_list_collections
from .metadata import get_server_metadata

logger = logging.getLogger(__name__)


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
    server_conf = {
        "map": {
            "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "attribution": '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap contributors</a>',
        },
        "limits": {
            "default_items": 20,
            "max_items": 50,
            "max_distance_x": None,
            "max_distance_y": None,
            "max_distance_units": None,
            "on_exceed": "throttle",
        },
    }
    data_license = metadata.license or {}
    data_provider = metadata.data_provider or {}
    point_of_contact = metadata.point_of_contact or {}
    unknown_detail = "unknown"

    pygeoapi_config = {
        "server": {
            "admin": server_conf.get("admin", False),  # we don't use pygeoapi's admin, but rather provide our own
            "languages": languages,
            "limits": server_conf["limits"],
            "map": server_conf["map"],
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
                "keywords_type": metadata.keywords_type or unknown_detail,
                "terms_of_service": metadata.terms_of_service or unknown_detail,
                "url": metadata.url or unknown_detail,
            },
            "license": {
                "name": data_license.get("name", unknown_detail),
                "url": data_license.get("url", unknown_detail),
            },
            "provider": {
                "name": data_provider.get("name", "Organization Name"),
                "url": data_provider.get("url"),
            },
            "contact": {
                "name": point_of_contact.get("name", "Lastname, Firstname"),
                "position": point_of_contact.get("position", "Position Title"),
                "address": point_of_contact.get("address", "Mailing Address"),
                "city": point_of_contact.get("city", "City"),
                "stateorprovince": point_of_contact.get("stateorprovince", "Administrative Area"),
                "postalcode": point_of_contact.get("postalcode", "Zip or Postal Code"),
                "country": point_of_contact.get("country", "Country"),
                "phone": point_of_contact.get("phone", "+xx-xxx-xxx-xxxx"),
                "fax": point_of_contact.get("fax", "+xx-xxx-xxx-xxxx"),
                "email": point_of_contact.get("email", "you@example.org"),
                "url": point_of_contact.get("url", "Contact URL"),
                "hours": point_of_contact.get("hours", "Mo-Fr 08:00-17:00"),
                "instructions": point_of_contact.get("instructions", "During hours of service. Off on weekends."),
                "role": point_of_contact.get("role", "pointOfContact"),
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


def _convert_collection_to_pygeoapi_resource(collection: Collection) -> dict:
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
    converted_providers = []
    for type_, provider in (collection.providers or {}).items():
        raw_data_value = provider.get("config", {}).pop("data", "")
        interpolated_data_value = re.sub(
            r"\${?(\w+)}?",
            lambda re_match: os.getenv(re_match.group(1), "ENV_VAR_NOT_FOUND"),
            raw_data_value,
        )
        converted_providers.append(
            {
                "type": type_,
                "data": interpolated_data_value,
                "name": provider.get("python_callable"),
                **provider.get("config", {}).get("options", {})
            }
        )

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
        "providers": converted_providers,
    }
