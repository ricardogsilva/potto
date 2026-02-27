import logging

from starlette_admin.contrib.sqlmodel import ModelView
from starlette_admin.fields import (
    CollectionField,
    JSONField,
    ListField,
    StringField,
    URLField,
)

from ...db import models
from .fields import SpatialExtentField

logger = logging.getLogger(__name__)


class CollectionResourceView(ModelView):
    fields = (
        models.CollectionResource.resource_identifier,
        models.CollectionResource.title,
        models.CollectionResource.description,
        SpatialExtentField(name="spatial_extent"),
        models.CollectionResource.temporal_extent_begin,
        models.CollectionResource.temporal_extent_end,
        models.CollectionResource.keywords,
        ListField(
            JSONField(name="providers"),
        ),
        ListField(
            CollectionField(
                name="additional_links",
                fields=(
                    StringField(name="media_type"),
                    StringField(name="rel"),
                    URLField(name="href"),
                    JSONField(name="title"),
                    StringField(name="href_lang"),
                )
            )
        ),
    )

    exclude_fields_from_list = (
        "description",
        "additional_links",
        "keywords",
        "spatial_extent",
        "temporal_extent_begin",
        "temporal_extent_end",
    )
