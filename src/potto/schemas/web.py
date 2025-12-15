import datetime as dt
from typing import Annotated

from pygeoapi.api import (
    FORMAT_TYPES,
    F_JSON,
    F_JSONLD,
    F_HTML,
)
import pydantic

from ..webapp.protocols import UrlResolver
from .potto import (
    CollectionFeatureListResponse,
    FeatureResponse,
)
from . import (
    items,
    pygeoapi_config,
)
from .base import Link


class GeoJsonItem(pydantic.BaseModel):
    id_: str = pydantic.Field(alias="id")
    type_: Annotated[str, pydantic.Field(alias="type")] = "feature"
    properties: dict
    geometry: dict

    @classmethod
    def from_potto(
            cls,
            potto_response: FeatureResponse,
            url_resolver: UrlResolver
    ) -> "GeoJsonItem":
        raise NotImplementedError


class GeoJsonItemCollection(pydantic.BaseModel):
    type: str
    features: list[dict]
    links: list[Link]
    number_matched: int = pydantic.Field(alias="numberMatched")
    number_returned: int = pydantic.Field(alias="numberReturned")
    timestamp: str = pydantic.Field(alias="timeStamp")

    @classmethod
    def from_potto(
            cls,
            potto_response: CollectionFeatureListResponse,
            url_resolver: UrlResolver
    ) -> "GeoJsonItemCollection":
        pagination_links = potto_response.pagination.get_links(
            str(
                url_resolver(
                    "list-collection-items",
                    collection_id=potto_response.resource.identifier
                )
            ),
            additional_query_params=potto_response.filter_.as_kwargs()
        )
        return cls(
            type="FeatureCollection",
            features=[
                feat.as_geojson(potto_response.resource, url_resolver)
                for feat in potto_response.features
            ],
            links=[
                Link(
                    type=FORMAT_TYPES[F_JSON],
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
                    type=FORMAT_TYPES[F_JSONLD],
                    rel="alternate",
                    href=str(
                        url_resolver(
                            "list-collection-items",
                            collection_id=potto_response.resource.identifier
                        )
                    ),
                    title="This document as JSON-LD"
                ),
                Link(
                    type=FORMAT_TYPES[F_HTML],
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
                    type=FORMAT_TYPES[F_HTML],
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
            potto_response: CollectionFeatureListResponse,
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
    pagination: items.FeatureCollectionPaginationContext
    filter_: items.FeatureCollectionFilter
    links: list[Link]

    @classmethod
    def from_potto(
        cls,
        potto_response: CollectionFeatureListResponse,
        url_resolver: UrlResolver
    ) -> "HtmlItemCollection":
        pagination_links = potto_response.pagination.get_links(
            str(
                url_resolver(
                    "list-collection-items",
                    collection_id=potto_response.resource.identifier
                )
            ),
            target_media_type=F_HTML,
            additional_query_params=potto_response.filter_.as_kwargs()
        )
        return cls(
            resource=potto_response.resource,
            provider=potto_response.provider,
            features={
                "type": "FeatureCollection",
                "features": [
                    f.as_geojson(potto_response.resource, url_resolver)
                    for f in potto_response.features
                ],
            },
            pagination=potto_response.pagination,
            filter_=potto_response.filter_,
            links=[
                *pagination_links,
                Link(
                    type=FORMAT_TYPES[F_HTML],
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
                    type=FORMAT_TYPES[F_JSON],
                    rel="alternate",
                    href=str(
                        url_resolver(
                            "list-collection-items",
                            collection_id=potto_response.resource.identifier
                        )
                    ) + f"?f={F_JSON}",
                    title="This document as JSON"
                ),
                Link(
                    type=FORMAT_TYPES[F_JSONLD],
                    rel="alternate",
                    href=str(
                        url_resolver(
                            "list-collection-items",
                            collection_id=potto_response.resource.identifier
                        )
                    ) + f"?f={F_JSONLD}",
                    title="This document as JSON-LD"
                ),
            ],
        )