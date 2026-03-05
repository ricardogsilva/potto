import logging

from starlette.requests import Request
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


class _PottoAdminModelView(ModelView):

    def handle_exception(self, exc: Exception) -> None:
        logger.exception("An error occurred", exc)
        return super().handle_exception(exc)


class CollectionItemView(_PottoAdminModelView):
    fields = (
        models.CollectionItem.resource_identifier,
        models.CollectionItem.collection_type,
        models.CollectionItem.title,
        models.CollectionItem.description,
        SpatialExtentField(name="spatial_extent"),
        models.CollectionItem.temporal_extent_begin,
        models.CollectionItem.temporal_extent_end,
        models.CollectionItem.keywords,
        JSONField(name="providers"),
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
        "providers",
    )
