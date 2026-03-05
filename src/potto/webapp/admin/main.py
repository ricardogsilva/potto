import logging
from pathlib import Path
from typing import Optional

from starlette.requests import Request
from starlette_admin.contrib.sqlmodel import Admin

from ...config import PottoSettings
from ...db import models
from . import views

logger = logging.getLogger(__name__)


class PottoAdmin(Admin):
    def custom_render_js(self, request: Request) -> Optional[str]:
        return str(request.url_for("static", path="js/admin/listRender.js"))


def create_admin_app_from_settings(settings: PottoSettings) -> Admin:
    templates_dir = str(
        settings.admin_templates_dir or
        Path(__file__).parents[1] / "templates/admin"
    )
    app = PottoAdmin(
        settings.get_sync_db_engine(),
        templates_dir=templates_dir,
        statics_dir=str(
            settings.static_dir or Path(__file__).parents[1] / "static"),
        title="Potto admin",
    )
    app.add_view(
        views.CollectionItemView(
            models.CollectionItem, identity="collection_item",)
    )
    return app