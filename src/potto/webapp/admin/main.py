import logging
from pathlib import Path
from starlette_admin.contrib.sqlmodel import Admin

from ...config import PottoSettings
from ...db import models
from . import views

logger = logging.getLogger(__name__)


def create_admin_app_from_settings(settings: PottoSettings) -> Admin:
    templates_dir = str(
        settings.admin_templates_dir or
        Path(__file__).parents[1] / "templates/admin"
    )
    app = Admin(
        settings.get_sync_db_engine(),
        templates_dir=templates_dir,
        statics_dir=str(
            settings.static_dir or Path(__file__).parents[1] / "static"),
        title="Potto admin",
    )
    app.add_view(views.CollectionResourceView(models.CollectionResource))
    return app