import contextlib
import logging
from typing import (
    AsyncIterator,
    TypedDict,
)

import jinja2
from pygeoapi.api import API
from pygeoapi.openapi import get_oas_30
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette_babel.contrib.jinja import configure_jinja_env
from starlette.templating import Jinja2Templates
from starlette_babel import (
    get_translator,
    LocaleMiddleware,
)

from .. import config
from .routes.base import routes as base_routes
from . import jinjafilters

logger = logging.getLogger(__name__)


class AppState(TypedDict):
    settings: config.PygeoapiStarletteSettings
    pygeoapi: API
    templates: Jinja2Templates


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[AppState]:
    settings = config.get_settings()
    pygeoapi_config = config.get_pygeoapi_settings(settings)
    openapi_document = get_oas_30(pygeoapi_config, fail_on_invalid_collection=True)
    pygeoapi_ = API(
        config=pygeoapi_config,
        openapi=openapi_document
    )
    if settings.translations_dir:
        shared_translator = get_translator()
        shared_translator.load_from_directory(settings.translations_dir)
    template_loaders: list[jinja2.BaseLoader] = [
        jinja2.PackageLoader("pygeoapi_starlette.webapp", "templates"),
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
    })
    configure_jinja_env(jinja_env)
    yield AppState(
        settings = settings,
        templates=Jinja2Templates(env=jinja_env),
        pygeoapi=pygeoapi_,
    )


def create_app() -> Starlette:
    settings = config.get_settings()
    return create_app_from_settings(settings)


def create_app_from_settings(settings: config.PygeoapiStarletteSettings) -> Starlette:
    if settings.static_dir is not None:
        settings.static_dir.mkdir(parents=True, exist_ok=True)
    app = Starlette(
        debug=settings.debug,
        routes=[
            Mount("/", routes=base_routes),
            Mount(
                "/static",
                app=StaticFiles(
                    directory=settings.static_dir,
                    packages=[("pygeoapi", "static")]
                ),
                name="static"
            ),
        ],
        middleware=[
            Middleware(
                LocaleMiddleware,
                locales=settings.locales,
                default_locale=settings.locales[0]
            ),
            Middleware(
                SessionMiddleware,
                secret_key=settings.session_secret_key,
            ),
            Middleware(
                GZipMiddleware,
                minimum_size=1000, compresslevel=9
            )
        ],
        lifespan=lifespan,
    )
    return app
