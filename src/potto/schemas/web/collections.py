from typing import Annotated

import pydantic

from ... import constants
from ...db import models
from ...webapp.protocols import UrlResolver
from .. import base


class JsonCollection(pydantic.BaseModel):
    id_: Annotated[str, pydantic.Field(alias="id")]
    title: base.Title
    description: base.MaybeDescription
    links: list[base.Link]
    extent: base.Extent | None = None
    item_type: Annotated[str | None, pydantic.Field(alias="itemType")] = constants.FEATURE_COLLECTION_ITEM_TYPE
    crs: list[str] = pydantic.Field(default_factory=lambda : [constants.CRS_84])

    @classmethod
    def from_db_item(
            cls,
            item: models.Collection,
            url_resolver: UrlResolver
    ) -> "JsonCollection":
        spatial_extent = base.TwoDimensionalSpatialExtent(
            bbox=item.spatial_extent.bounds
        ) if item.spatial_extent else None
        temporal_extent = base.TemporalExtent(
            interval=[
                (
                    item.temporal_extent_begin.isoformat() if item.temporal_extent_begin else None,
                    item.temporal_extent_end.isoformat() if item.temporal_extent_end else None
                )
            ]
        ) if (item.temporal_extent_begin or item.temporal_extent_end) else None
        return cls(
            id_=item.resource_identifier,
            title=item.title,
            description=item.description,
            links=[],  # TODO: add links
            extent=base.Extent(
                spatial=spatial_extent,
                temporal=temporal_extent
            ) if (temporal_extent or spatial_extent) else None
        )


class JsonCollectionList(pydantic.BaseModel):
    links: list[base.Link]
    collections: list[JsonCollection]

    @classmethod
    def from_db_items(
            cls,
            items: list[models.Collection],
            url_resolver: UrlResolver
    ) -> "JsonCollectionList":
        return cls(
            collections=[JsonCollection.from_db_item(i, url_resolver) for i in items],
            links=[]
        )


