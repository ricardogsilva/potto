import logging

from starlette_admin.contrib.sqlmodel import ModelView
from .fields import SpatialExtentField

logger = logging.getLogger(__name__)


class CollectionResourceView(ModelView):
    fields = (
        "title",
        SpatialExtentField(name="spatial_extent"),
    )