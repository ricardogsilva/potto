from pygeoapi.api import (
    FORMAT_TYPES,
    F_JSON,
    F_JSONLD,
    F_HTML,
)
import pydantic

from .potto import PottoStructuredResponse
from .items import (
    Feature,
    UrlResolver,
)
from .pygeoapi_config import (
    ItemCollectionConfig,
)


class Link(pydantic.BaseModel):
    media_type: str = pydantic.Field(alias="type")
    rel: str
    href: str
    title: str | None = None
    href_lang: str | None = None
    length: int | None = None


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
            potto_response: PottoStructuredResponse,
            url_resolver: UrlResolver
    ) -> "GeoJsonItemCollection":
        return cls(
            type="FeatureCollection",
            features=[feat.as_geojson() for feat in potto_response.content.features],
            links=[
                Link(
                    type=FORMAT_TYPES[F_JSON],
                    rel="self",
                    href=str(
                        url_resolver(
                            "list-collection-items",
                            collection_id=potto_response.context.resource.identifier
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
                            collection_id=potto_response.context.resource.identifier
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
                            collection_id=potto_response.context.resource.identifier
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
                            collection_id=potto_response.context.resource.identifier
                        )
                    ),
                    title=potto_response.context.resource.title
                ),
            ],
            numberMatched=potto_response.content.number_matched,
            numberReturned=potto_response.content.number_returned,
            timeStamp=potto_response.content.timestamp,
        )


class JsonLdItemCollection(pydantic.BaseModel):
    context: dict = pydantic.Field(serialization_alias="@context")
    id_: str = pydantic.Field(serialization_alias="@id")
    type: str
    features: list[dict]

    @classmethod
    def from_potto(
            cls,
            potto_response: PottoStructuredResponse,
            url_resolver: UrlResolver
    ) -> "JsonLdItemCollection":
        detail_url = url_resolver(
            "get-collection",
            collection_id=potto_response.context.resource.identifier,
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
                    potto_response.context.resource,
                    url_resolver
                ) for feat in potto_response.content.features
            ]
        )


class HtmlItemCollection(pydantic.BaseModel):
    resource: ItemCollectionConfig
    features: list[Feature]
    links: list[Link]
    number_matched: int = pydantic.Field(alias="numberMatched")
    number_returned: int = pydantic.Field(alias="numberReturned")
    timestamp: str = pydantic.Field(alias="timeStamp")

    @classmethod
    def from_potto(
        cls,
        potto_response: PottoStructuredResponse,
        url_resolver: UrlResolver
    ) -> "HtmlItemCollection":
        return cls(
            resource=potto_response.context.resource,
            features=potto_response.content.features,
            links=[
                Link(
                    type=FORMAT_TYPES[F_HTML],
                    rel="self",
                    href=str(
                        url_resolver(
                            "list-collection-items",
                            collection_id=potto_response.context.resource.identifier
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
                            collection_id=potto_response.context.resource.identifier
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
                            collection_id=potto_response.context.resource.identifier
                        )
                    ) + f"?f={F_JSONLD}",
                    title="This document as JSON-LD"
                ),
            ],
            numberMatched=potto_response.content.number_matched,
            numberReturned=potto_response.content.number_returned,
            timeStamp=potto_response.content.timestamp,
        )
