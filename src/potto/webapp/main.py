import contextlib
import logging
from typing import AsyncIterator

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.routing import (
    Mount,
    Route,
)
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette_babel import LocaleMiddleware

from .. import config
from ..authn.backend import LocalAuthBackend, OIDCAuthBackend
from ..wrapper import Potto
from .routes import (
    auth as auth_routes,
    ogcapi_common as ogc_api_common_routes,
    ogcapi_features as ogc_api_features_routes,
)
from .state import AppState
from .api.main import create_api_app_from_settings
from .admin.main import create_admin_app_from_settings

logger = logging.getLogger(__name__)


_default_app_state: AppState | None = None


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[AppState]:
    settings = config.get_settings()
    oidc_provider = settings.get_oidc_provider()
    if oidc_provider is not None:
        await oidc_provider.get_discovery()
    global _default_app_state
    _default_app_state = AppState(
        settings=settings,
        templates=Jinja2Templates(env=settings.get_jinja_env()),
        potto=Potto(settings),
        oidc_provider=oidc_provider,
        authorization_backend=settings.get_authorization_backend(),
    )
    yield _default_app_state
    _default_app_state = None


def create_app() -> Starlette:
    settings = config.get_settings()
    return create_app_from_settings(settings)


def create_app_from_settings(settings: config.PottoSettings) -> Starlette:
    if settings.static_dir is not None:
        settings.static_dir.mkdir(parents=True, exist_ok=True)
    oidc_provider = settings.get_oidc_provider()
    auth_backend = (
        OIDCAuthBackend(settings, oidc_provider)
        if oidc_provider is not None
        else LocalAuthBackend(settings)
    )
    app = Starlette(
        debug=settings.debug,
        routes=get_routes(settings, enable_ogcapi_features=True),
        middleware=[
            Middleware(
                LocaleMiddleware,
                locales=settings.locales,
                default_locale=settings.locales[0]
            ),
            Middleware(
                SessionMiddleware,
                secret_key=settings.session_secret_key.get_secret_value(),
            ),
            Middleware(
                AuthenticationMiddleware,
                backend=auth_backend,
            ),
            Middleware(
                GZipMiddleware,
                minimum_size=1000, compresslevel=9
            )
        ],
        lifespan=lifespan,
    )
    admin_app = create_admin_app_from_settings(settings)
    admin_app.mount_to(app)
    return app


def get_routes(
        settings: config.PottoSettings,
        enable_ogcapi_features: bool = False,
) -> list[Route | Mount]:
    routes: list[Route | Mount] = []
    if settings.oidc is not None:
        routes += [
            Route("/auth/oidc/login", auth_routes.oidc_login, name="oidc-login"),
            Route("/auth/oidc/callback", auth_routes.oidc_callback, name="oidc-callback"),
        ]
    routes += [
        Route("/", ogc_api_common_routes.get_landing_page, name="landing-page"),
        Route(
            "/conformance",
            ogc_api_common_routes.get_conformance_details,
            name="conformance-document"
        ),
        Route(
            "/openapi",
            ogc_api_common_routes.get_openapi_document,
            name="openapi-document"
        ),
    ]
    if enable_ogcapi_features:
        routes.extend([
            Route(
                "/collections/{collection_id}/items/{item_id}",
                ogc_api_features_routes.get_item_details,
                name="get-item"
            ),
            Route(
                "/collections/{collection_id}/items",
                ogc_api_features_routes.list_collection_items,
                name="list-collection-items"
            ),
            Route(
                "/collections/{collection_id}",
                ogc_api_features_routes.get_collection_details,
                name="get-collection"
            ),
            Route(
                "/collections",
                ogc_api_features_routes.list_collections,
                name="list-collections"
            ),
        ])
    api_app = create_api_app_from_settings(settings)
    routes.extend([
        Mount(
            "/api",
            app=api_app,
            name="api"
        ),
        Mount(
            "/static",
            app=StaticFiles(
                directory=settings.static_dir,
                packages=[
                    ("potto", "webapp/static"),
                    ("pygeoapi", "static")
                ]
            ),
            name="static"
        ),
    ])
    return routes
