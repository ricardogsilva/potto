import datetime as dt
import json
from typing import (
    Annotated,
    Sequence,
)

import pydantic
import shapely

from ... import constants
from ...webapp.protocols import UrlResolver
from ...webapp.util import get_base_links
from .. import (
    base,
    pygeoapi_config,
    potto as potto_schemas,
)
from ..base import FeatureFilter, Link


class GeoJsonItem(pydantic.BaseModel):
    id_: str = pydantic.Field(serialization_alias="id")
    type_: Annotated[str, pydantic.Field(serialization_alias="type")] = "feature"
    properties: dict
    geometry: dict
    links: list[Link]

    @classmethod
    def from_potto(
        cls,
        potto_response: potto_schemas.FeatureResponse,
        url_resolver: UrlResolver,
        exclude_link_relations: Sequence[str] | None = None,
    ) -> "GeoJsonItem":
        all_links = [
            Link(
                type=constants.MEDIA_TYPE_GEO_JSON,
                rel=constants.REL_SELF,
                href=str(
                    url_resolver(
                        "api:collection-item-get",
                        collection_id=potto_response.collection.identifier,
                        item_id=potto_response.feature.id_,
                    )
                ),
                title="Details about this feature",
            ),
            Link(
                type=constants.MEDIA_TYPE_JSON,
                rel=constants.REL_COLLECTION,
                href=str(
                    url_resolver(
                        "api:collection-get",
                        collection_id=potto_response.collection.identifier,
                    )
                ),
                title="This feature's collection",
            ),
        ]
        return cls(
            id_=potto_response.feature.id_,
            properties=potto_response.feature.properties,
            type_="Feature",
            geometry=json.loads(shapely.to_geojson(potto_response.feature.geometry)),
            links=[
                link
                for link in all_links
                if link.rel not in (exclude_link_relations or [])
            ],
        )


class GeoJsonItemCollection(pydantic.BaseModel):
    type: str
    features: list[GeoJsonItem]
    links: list[Link]
    number_matched: int = pydantic.Field(serialization_alias="numberMatched")
    number_returned: int = pydantic.Field(serialization_alias="numberReturned")
    time_stamp: str = pydantic.Field(serialization_alias="timeStamp")

    @classmethod
    def from_potto(
        cls,
        potto_response: potto_schemas.FeatureListResponse,
        url_resolver: UrlResolver,
    ) -> "GeoJsonItemCollection":
        now = dt.datetime.now(tz=dt.timezone.utc).isoformat()
        return cls(
            type="FeatureCollection",
            features=[
                GeoJsonItem.from_potto(
                    potto_schemas.FeatureResponse(potto_response.collection, feat),
                    url_resolver,
                    exclude_link_relations=("collection",),
                )
                for feat in potto_response.features
            ],
            links=cls.get_links(url_resolver, potto_response),
            number_matched=potto_response.pagination.number_matched,
            number_returned=potto_response.pagination.number_returned,
            time_stamp=(
                potto_response.metadata.get("timestamp") or now
                if potto_response.metadata is not None
                else now
            ),
        )

    @classmethod
    def get_links(
        cls,
        url_resolver: UrlResolver,
        potto_response: potto_schemas.FeatureListResponse,
    ) -> list[Link]:
        pagination_links = potto_response.pagination.get_links(
            str(
                url_resolver(
                    "api:collection-item-list",
                    collection_id=potto_response.collection.identifier,
                )
            ),
            additional_query_params=(
                potto_response.filter_.model_dump(
                    by_alias=True, exclude_none=True, exclude={"offset"}
                )
                if potto_response.filter_
                else None
            ),
        )
        return [
            *get_base_links(url_resolver),
            Link(
                type=constants.MEDIA_TYPE_GEO_JSON,
                rel=constants.REL_SELF,
                href=str(
                    url_resolver(
                        "api:collection-item-list",
                        collection_id=potto_response.collection.identifier,
                    )
                ),
                title="This document",
            ),
            Link(
                type=constants.MEDIA_TYPE_JSON,
                rel=constants.REL_COLLECTION,
                href=str(
                    url_resolver(
                        "api:collection-get",
                        collection_id=potto_response.collection.identifier,
                    )
                ),
                # TODO: localize this
                title=(
                    potto_response.collection.title.get("en", "")
                    if isinstance(potto_response.collection.title, dict)
                    else potto_response.collection.title
                ),
            ),
            *pagination_links,
        ]


class HtmlItemCollection(pydantic.BaseModel):
    collection: potto_schemas.Collection
    features: dict
    pagination: base.PaginationContext
    filter_: FeatureFilter | None
    links: list[Link]

    @classmethod
    def from_potto(
        cls,
        potto_response: potto_schemas.FeatureListResponse,
        url_resolver: UrlResolver,
    ) -> "HtmlItemCollection":
        pagination_links = potto_response.pagination.get_links(
            str(
                url_resolver(
                    "list-collection-items",
                    collection_id=potto_response.collection.identifier,
                )
            ),
            target_media_type=constants.MEDIA_TYPE_HTML,
            additional_query_params=potto_response.filter_.model_dump(by_alias=True)
            if potto_response.filter_
            else None,
        )
        return cls(
            collection=potto_response.collection,
            features={
                "type": "FeatureCollection",
                "features": [
                    GeoJsonItem.from_potto(
                        potto_schemas.FeatureResponse(
                            collection=potto_response.collection, feature=feat
                        ),
                        url_resolver,
                        exclude_link_relations=("collection",),
                    )
                    for feat in potto_response.features
                ],
            },
            pagination=potto_response.pagination,
            filter_=potto_response.filter_,
            links=[
                *pagination_links,
                Link(
                    type=constants.MEDIA_TYPE_HTML,
                    rel="self",
                    href=str(
                        url_resolver(
                            "list-collection-items",
                            collection_id=potto_response.collection.identifier,
                        )
                    ),
                    title="This document",
                ),
                Link(
                    type=constants.MEDIA_TYPE_JSON,
                    rel="alternate",
                    href=str(
                        url_resolver(
                            "api:list-collection-items",
                            collection_id=potto_response.collection.identifier,
                        )
                    ),
                    title="This document as JSON",
                ),
            ],
        )


class HtmlItemFeature(pydantic.BaseModel):
    resource: pygeoapi_config.ItemCollectionConfig
    provider: pygeoapi_config.ProviderConfig
    feature: GeoJsonItem
    links: list[Link]
