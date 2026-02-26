import logging

from starlette_admin.contrib.sqlmodel import ModelView

from ...db import models
from .fields import SpatialExtentField

logger = logging.getLogger(__name__)


class CollectionResourceView(ModelView):
    fields = (
        models.CollectionResource.resource_identifier,
        models.CollectionResource.title,
        models.CollectionResource.description,
        models.CollectionResource.keywords,
        SpatialExtentField(name="spatial_extent"),
    )