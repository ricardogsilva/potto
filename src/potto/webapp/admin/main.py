import logging
from pathlib import Path
from typing import Optional

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette_admin.contrib.sqlmodel import Admin

from ...config import PottoSettings
from ...db.models import Collection
from . import views
from .auth import (
    LocalAdminAuthProvider,
    OIDCAdminAuthProvider
)

logger = logging.getLogger(__name__)


class PottoAdmin(Admin):
    potto_settings: PottoSettings

    def __init__(self, *args, potto_settings: PottoSettings, **kwargs):
        super().__init__(*args, **kwargs)
        self.potto_settings = potto_settings


    def mount_to(
            self,
            app: Starlette,
            redirect_slashes: bool = True
    ) -> None:
        """Reimplemented in order to pass settings to the admin app."""
        admin_app = Starlette(
            routes=self.routes,
            middleware=self.middlewares,
            debug=self.debug,
            exception_handlers={HTTPException: self._render_error},
        )
        admin_app.state.ROUTE_NAME = self.route_name
        admin_app.state.SETTINGS = self.potto_settings
        app.mount(
            self.base_url,
            app=admin_app,
            name=self.route_name,
        )
        admin_app.router.redirect_slashes = redirect_slashes

    def custom_render_js(self, request: Request) -> Optional[str]:
        return str(request.url_for("static", path="js/admin/listRender.js"))


def create_admin_app_from_settings(settings: PottoSettings) -> Admin:
    templates_dir = str(
        settings.admin_templates_dir or
        Path(__file__).parents[1] / "templates/admin"
    )
    auth_provider = (
        OIDCAdminAuthProvider(settings) if settings.oidc is not None
        else LocalAdminAuthProvider(settings)
    )
    app = PottoAdmin(
        settings.get_sync_db_engine(),
        potto_settings=settings,
        auth_provider=auth_provider,
        templates_dir=templates_dir,
        statics_dir=str(
            settings.static_dir or Path(__file__).parents[1] / "static"),
        title="Potto admin",
    )
    app.add_view(
        views.CollectionItemView(
            Collection, identity="collection_item",)
    )
    return app