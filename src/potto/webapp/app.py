import contextlib
import logging
from typing import (
    AsyncIterator,
    TypedDict,
)

import jinja2
from pygeoapi import __version__ as pygeoapi_version
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.routing import (
    Mount,
    Route,
)
from starlette.staticfiles import StaticFiles
from starlette_babel.contrib.jinja import configure_jinja_env
from starlette.templating import Jinja2Templates
from starlette_babel import (
    get_translator,
    LocaleMiddleware,
)

from .. import config
from ..wrapper import Potto
from . import jinjafilters
from .routes import (
    ogcapi_common as ogc_api_common_routes,
    ogcapi_features as ogc_api_features_routes,
)

logger = logging.getLogger(__name__)


class AppState(TypedDict):
    settings: config.PottoSettings
    potto: Potto
    templates: Jinja2Templates


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[AppState]:
    settings = config.get_settings()
    if settings.translations_dir:
        shared_translator = get_translator()
        shared_translator.load_from_directory(settings.translations_dir)
    template_loaders: list[jinja2.BaseLoader] = [
        jinja2.PackageLoader("potto.webapp", "templates"),
        jinja2.PackageLoader("pygeoapi", "templates"),
    ]
    if settings.templates_dir:
        template_loaders.append(
            jinja2.FileSystemLoader(settings["templates_dir"]),
        )
    jinja_env = jinja2.Environment(
        loader=jinja2.ChoiceLoader(template_loaders),
        autoescape=True,
        extensions=[
            "jinja2.ext.i18n",
        ]
    )
    jinja_env.filters.update({
        "to_json": jinjafilters.to_json,
        "format_datetime": jinjafilters.format_datetime,
        "format_duration": jinjafilters.format_duration,
        "human_size": jinjafilters.human_size,
        "get_path_basename": jinjafilters.get_path_basename,
        "get_breadcrumbs": jinjafilters.get_breadcrumbs,
        "filter_dict_by_key_value": jinjafilters.filter_dict_by_key_value,
    })
    jinja_env.globals.update({
        "settings": settings,
        "pygeoapi_version": pygeoapi_version,
    })
    configure_jinja_env(jinja_env)
    yield AppState(
        settings = settings,
        templates=Jinja2Templates(env=jinja_env),
        potto=Potto.from_settings(settings),
    )


def create_app() -> Starlette:
    settings = config.get_settings()
    return create_app_from_settings(settings)


def create_app_from_settings(settings: config.PottoSettings) -> Starlette:
    if settings.static_dir is not None:
        settings.static_dir.mkdir(parents=True, exist_ok=True)
    app = Starlette(
        debug=settings.debug,
        routes=get_routes(
            settings,
            enable_ogcapi_features=True,
        ),
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
                GZipMiddleware,
                minimum_size=1000, compresslevel=9
            )
        ],
        lifespan=lifespan,
    )
    return app


def get_routes(
        settings: config.PottoSettings,
        enable_ogcapi_features: bool = False,
) -> list[Route]:
    routes: list[Route | Mount] = [
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
    routes.extend([
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
