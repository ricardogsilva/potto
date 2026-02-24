from starlette_admin.contrib.sqlmodel import (
    Admin,
    ModelView,
)

from ...config import PottoSettings
from ...db import models
from ...db.engine import get_sync_engine


def create_admin_app_from_settings(settings: PottoSettings) -> Admin:
    app = Admin(get_sync_engine(settings.database_dsn.unicode_string()))
    app.add_view(ModelView(models.CollectionResource))
    return app