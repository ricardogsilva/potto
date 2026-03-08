import datetime as dt
import json
from typing import (
    Annotated,
    Literal,
    Mapping,
    Sequence,
)

import pydantic
import shapely

from ...db import models
from ... import constants
from ...webapp.protocols import UrlResolver
from .. import (
    pygeoapi_config,
    potto, items, base,
)
from ..base import Link


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


class FeatureFilter(ItemFilter):
    crs: str | None = None

    @classmethod
    def from_query_parameters(
            cls,
            params: Mapping[str, str | Sequence[str]],
    ) -> "FeatureFilter":
        return cls(
            bbox=params.get("bbox"),
            bbox_crs=params.get("bbox-crs"),
            crs=params.get("crs"),
            datetime_=params.get("datetime"),
            filter_=params.get("filter"),
            filter_crs_uri=params.get("filter-crs"),
            filter_lang=params.get("filter-lang"),
            limit=int(params.get("limit", 20)),
            offset=int(params.get("offset", 0)),
            extra_properties=dict(params),
            query=params.get("q"),
            result_type=params.get("resulttype", "results"),
            sort_by=params.get("sortby"),
            skip_geometry=(
                True
                if params.get("skipGeometry", "").lower()
                   in ("true", "yes", "on", "t", "1") else False
            ),
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
            feature: items.Feature,
            collection: models.Collection,
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
                        collection_id=collection.resource_identifier,
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
                        collection_id=collection.resource_identifier,
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
                        collection_id=collection.resource_identifier,
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
                        collection_id=collection.resource_identifier,
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
            potto_response: potto.FeatureListResponse,
            url_resolver: UrlResolver
    ) -> "GeoJsonItemCollection":
        pagination_links = potto_response.pagination.get_links(
            str(
                url_resolver(
                    "list-collection-items",
                    collection_id=potto_response.collection.resource_identifier
                )
            ),
            additional_query_params=potto_response.filter_.model_dump(
                by_alias=True, exclude_none=True, exclude={"offset"})
        )
        return cls(
            type="FeatureCollection",
            features=[
                GeoJsonItem.from_potto(
                    feat, potto_response.collection, url_resolver,
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
                            collection_id=potto_response.collection.resource_identifier
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
                            collection_id=potto_response.collection.resource_identifier
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
                            collection_id=potto_response.collection.resource_identifier
                        )
                    ),
                    # TODO: localize this
                    title=potto_response.collection.title
                ),
                *pagination_links,
            ],
            numberMatched=potto_response.pagination.number_matched,
            numberReturned=potto_response.pagination.number_returned,
            timeStamp=potto_response.metadata.get(
                "timestamp", dt.datetime.now(tz=dt.timezone.utc).isoformat()),
        )


class HtmlItemCollection(pydantic.BaseModel):
    resource: pygeoapi_config.ItemCollectionConfig
    provider: pygeoapi_config.ProviderConfig
    features: dict
    pagination: base.PaginationContext
    filter_: FeatureFilter
    links: list[Link]

    @classmethod
    def from_potto(
            cls,
            potto_response: potto.FeatureListResponse,
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
