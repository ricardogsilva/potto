import datetime as dt
import json
from typing import (
    Annotated,
    Literal,
    Sequence,
)

import pydantic
import shapely

from ... import constants
from ...webapp.protocols import UrlResolver
from ..base import (
    Extent,
    Link,
)
from .. import (
    collections as internal_collections,
    pygeoapi_config,
    potto,
)


class ItemFilter(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="allow")

    bbox: str | None = None
    bbox_crs: Annotated[str | None, pydantic.Field(alias="bbox-crs")] = None
    cql_text: str | None = None
    datetime_: Annotated[str | None, pydantic.Field(alias="datetime")] = None
    extra_properties: dict[str, str] | None = None
    filter_: Annotated[str | None, pydantic.Field(alias="filter")] = None
    filter_lang: str | None = None
    filter_crs_uri: str | None = None
    limit: int = 20
    locale: Annotated[str | None, pydantic.Field(alias="language")] = None
    offset: int = 0
    query: str | None = None
    result_type: Literal["hits", "results"] = "results"
    select_properties: Annotated[list[str] | None, pydantic.Field(alias="properties")] = None
    skip_geometry: Annotated[bool | None, pydantic.Field(alias="skipGeometry")] = None
    sort_by: Annotated[str | None, pydantic.Field(alias="sortby")] = None


class JsonCollection(pydantic.BaseModel):
    id_: Annotated[str, pydantic.Field(alias="id")]
    title: str | None = None
    description: str | None = None
    links: list[Link]
    extent: Extent | None = None
    item_type: Annotated[str | None, pydantic.Field(alias="itemType")] = constants.FEATURE_COLLECTION_ITEM_TYPE
    crs: list[str] = pydantic.Field(default_factory=lambda : [constants.CRS_84])

    @classmethod
    def from_potto(
            cls,
            collection: internal_collections.Collection,
            url_resolver: UrlResolver
    ) -> "JsonCollection":
        return cls(
            **collection.model_dump(by_alias=True),
            links=[]
        )


class JsonCollectionList(pydantic.BaseModel):
    links: list[Link]
    collections: list[JsonCollection]

    @classmethod
    def from_potto(
            cls,
            potto_result: potto.CollectionList,
            url_resolver: UrlResolver
    ) -> "JsonCollectionList":
        return cls(
            collections=[
                JsonCollection.from_potto(c, url_resolver)
                for c in potto_result.collections
            ],
            links=[]
        )


class GeoJsonItem(pydantic.BaseModel):
    id_: str = pydantic.Field(alias="id")
    type_: Annotated[str, pydantic.Field(alias="type")] = "feature"
    properties: dict
    geometry: dict
    links: list[Link]

    @classmethod
    def from_potto(
            cls,
            feature: internal_collections.Feature,
            resource: pygeoapi_config.ItemCollectionConfig,
            url_resolver: UrlResolver,
            exclude_link_relations: Sequence[str] | None = None
    ) -> "GeoJsonItem":
        all_links = [
            Link(
                type="application/geo+json",
                rel="self",
                href=str(
                    url_resolver(
                        "api:get-item",
                        collection_id=resource.identifier,
                        item_id=feature.id_
                    )
                ),
                title="Details about this feature",
            ),
            Link(
                type=constants.MEDIA_TYPE_HTML,
                rel="alternate",
                href=str(
                    url_resolver(
                        "get-item",
                        collection_id=resource.identifier,
                        item_id=feature.id_
                    )
                ),
                title="Details about this feature as HTML",
            ),
            Link(
                type=constants.MEDIA_TYPE_JSON,
                rel="collection",
                href=str(
                    url_resolver(
                        "api:get-collection",
                        collection_id=resource.identifier,
                    )
                ),
                title="This feature's collection",
            ),
            Link(
                type=constants.MEDIA_TYPE_HTML,
                rel="collection",
                href=str(
                    url_resolver(
                        "get-collection",
                        collection_id=resource.identifier,
                    )
                ),
                title="This feature's collection as HTML",
            ),
        ]
        return cls(
            **feature.model_dump(exclude={"geometry"}, by_alias=True),
            type_="Feature",
            geometry=json.loads(shapely.to_geojson(feature.geometry)),
            links=[link for link in all_links if link.rel not in (exclude_link_relations or [])]
        )


class GeoJsonItemCollection(pydantic.BaseModel):
    type: str
    features: list[GeoJsonItem]
    links: list[Link]
    number_matched: int = pydantic.Field(alias="numberMatched")
    number_returned: int = pydantic.Field(alias="numberReturned")
    timestamp: str = pydantic.Field(alias="timeStamp")

    @classmethod
    def from_potto(
            cls,
            potto_response: potto.CollectionFeatureListResponse,
            url_resolver: UrlResolver
    ) -> "GeoJsonItemCollection":
        pagination_links = potto_response.pagination.get_links(
            str(
                url_resolver(
                    "list-collection-items",
                    collection_id=potto_response.resource.identifier
                )
            ),
            additional_query_params=potto_response.filter_.model_dump(
                by_alias=True, exclude_none=True, exclude={"offset"})
        )
        return cls(
            type="FeatureCollection",
            features=[
                GeoJsonItem.from_potto(
                    feat, potto_response.resource, url_resolver,
                    exclude_link_relations=("collection",)
                )
                for feat in potto_response.features
            ],
            links=[
                Link(
                    type=constants.MEDIA_TYPE_JSON,
                    rel="self",
                    href=str(
                        url_resolver(
                            "api:list-collection-items",
                            collection_id=potto_response.resource.identifier
                        )
                    ),
                    title="This document"
                ),
                Link(
                    type=constants.MEDIA_TYPE_HTML,
                    rel="alternate",
                    href=str(
                        url_resolver(
                            "list-collection-items",
                            collection_id=potto_response.resource.identifier
                        )
                    ),
                    title="This document as HTML"
                ),
                Link(
                    type=constants.MEDIA_TYPE_HTML,
                    rel="collection",
                    href=str(
                        url_resolver(
                            "get-collection",
                            collection_id=potto_response.resource.identifier
                        )
                    ),
                    title=potto_response.resource.title
                ),
                *pagination_links,
            ],
            numberMatched=potto_response.pagination.number_matched,
            numberReturned=potto_response.pagination.number_returned,
            timeStamp=potto_response.metadata.get(
                "timestamp", dt.datetime.now(tz=dt.timezone.utc).isoformat()),
        )


class JsonLdItemCollection(pydantic.BaseModel):
    context: dict = pydantic.Field(serialization_alias="@context")
    id_: str = pydantic.Field(serialization_alias="@id")
    type: str
    features: list[dict]

    @classmethod
    def from_potto(
            cls,
            potto_response: potto.CollectionFeatureListResponse,
            url_resolver: UrlResolver
    ) -> "JsonLdItemCollection":
        detail_url = url_resolver(
            "get-collection",
            collection_id=potto_response.resource.identifier,
        )
        return cls(
            context={
                "schema": "https://schema.org",
                "type": "@type",
                "features": "schema:itemListElement",
                "FeatureCollection": "schema:itemList",
            },
            id_=str(detail_url),
            type="FeatureCollection",
            features=[
                feat.as_jsonld(
                    potto_response.resource,
                    url_resolver
                ) for feat in potto_response.features
            ]
        )


class HtmlItemCollection(pydantic.BaseModel):
    resource: pygeoapi_config.ItemCollectionConfig
    provider: pygeoapi_config.ProviderConfig
    features: dict
    pagination: internal_collections.CollectionItemsPaginationContext
    filter_: internal_collections.FeatureFilter
    links: list[Link]

    @classmethod
    def from_potto(
            cls,
            potto_response: potto.CollectionFeatureListResponse,
            url_resolver: UrlResolver
    ) -> "HtmlItemCollection":
        pagination_links = potto_response.pagination.get_links(
            str(
                url_resolver(
                    "list-collection-items",
                    collection_id=potto_response.resource.identifier
                )
            ),
            target_media_type=constants.MEDIA_TYPE_HTML,
            additional_query_params=potto_response.filter_.model_dump(by_alias=True)
        )
        return cls(
            resource=potto_response.resource,
            provider=potto_response.provider,
            features={
                "type": "FeatureCollection",
                "features": [
                    GeoJsonItem.from_potto(
                        feat, potto_response.resource, url_resolver,
                        exclude_link_relations=("collection",)
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
                            collection_id=potto_response.resource.identifier
                        )
                    ),
                    title="This document"
                ),
                Link(
                    type=constants.MEDIA_TYPE_JSON,
                    rel="alternate",
                    href=str(
                        url_resolver(
                            "api:list-collection-items",
                            collection_id=potto_response.resource.identifier
                        )
                    ),
                    title="This document as JSON"
                ),
            ],
        )


class HtmlItemFeature(pydantic.BaseModel):
    resource: pygeoapi_config.ItemCollectionConfig
    provider: pygeoapi_config.ProviderConfig
    feature: GeoJsonItem
    links: list[Link]
