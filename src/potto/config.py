import warnings
from pathlib import Path
from typing import Any

import jinja2
import pydantic
import pydantic_settings
import sqlmodel
from pydantic.networks import PostgresDsn
from pygeoapi import __version__ as pygeoapi_version
from pygeoapi.util import yaml_load
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio.session import async_sessionmaker
from sqlalchemy.ext.asyncio.engine import (
    AsyncEngine,
    create_async_engine,
)
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette_babel import get_translator
from starlette_babel.contrib.jinja import configure_jinja_env

from . import jinjafilters

warnings.filterwarnings(
    "ignore",
    message="directory .* does not exist",
    module="pydantic_settings",
)


class PottoSettings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="potto__",
        env_nested_delimiter="__",
        secrets_dir="/run/secrets",
    )

    bind_host: str = "127.0.0.1"
    bind_port: int = 3001
    database_dsn: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://potto:pottopass@localhost/potto"
    )
    debug: bool = False
    public_url: str = "http://localhost:3001"
    pygeoapi_config_file: Path = Path.home() / "pygeoapi-config.yml"
    templates_dir: Path | None = None
    admin_templates_dir: Path | None = None
    translations_dir: Path | None = None
    locales: list[str] = ["en"]
    reload_dirs: str | list[str] | None = None
    session_secret_key: pydantic.SecretStr = "somesecretkey"
    static_dir: Path | None = None
    uvicorn_num_workers: int = 8
    uvicorn_log_config_file: Path | None = None

    _jinja_env: jinja2.Environment | None = None
    _db_engine: AsyncEngine | None = None
    _sync_db_engine: Engine | None = None
    _db_session_maker: async_sessionmaker | None = None

    def get_jinja_env(self) -> jinja2.Environment:
        if self._jinja_env is None:
            self._jinja_env = _get_jinja_env(self)
        return self._jinja_env

    def get_db_engine(self) -> AsyncEngine:
        if self._db_engine is None:
            self._db_engine = create_async_engine(
                self.database_dsn.unicode_string(), echo=self.debug
            )
        return self._db_engine

    def get_sync_db_engine(self) -> Engine:
        if self._sync_db_engine is None:
            self._sync_db_engine = sqlmodel.create_engine(
                self.database_dsn.unicode_string(),
                echo=self.debug
            )
        return self._sync_db_engine

    def get_db_session_maker(self) -> async_sessionmaker:
        if self._db_session_maker is None:
            self._db_session_maker = async_sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.get_db_engine(),
                expire_on_commit=False,
                class_=AsyncSession
            )
        return self._db_session_maker


def get_settings() -> PottoSettings:
    return PottoSettings()


def _get_jinja_env(settings: PottoSettings) -> jinja2.Environment:
    if settings.translations_dir:
        shared_translator = get_translator()
        shared_translator.load_from_directory(settings.translations_dir)
    template_loaders: list[jinja2.BaseLoader] = [
        jinja2.PackageLoader("potto.webapp", "templates"),
        jinja2.PackageLoader("pygeoapi", "templates"),
    ]
    if settings.templates_dir:
        template_loaders.insert(
            0,
            jinja2.FileSystemLoader(settings.templates_dir),
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
    return jinja_env


def get_pygeoapi_config(settings: PottoSettings) -> dict:
    read_conf = yaml_load(settings.pygeoapi_config_file.read_text())
    server_conf = read_conf.get("server", {})
    server_map = server_conf.get("map", {})
    server_limits_conf = server_conf.get("limits", {})
    metadata_conf = read_conf.get("metadata", {})
    identification_conf = metadata_conf.get("identification", {})
    license_conf = metadata_conf.get("license", {})
    provider_conf = metadata_conf.get("provider", {})
    contact_conf = metadata_conf.get("contact", {})
    return {
        "server": {
            "admin": server_conf.get("admin", False),
            "languages": settings.locales,
            "limits": {
                "default_items": server_limits_conf.get("default_items", 20),
                "max_items": server_limits_conf.get("max_items", 50),
            },
            "map": {
                "url": server_map.get(
                    "map", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
                "attribution": server_map.get(
                    "attribution",
                    '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap contributors</a>'
                ),
            },
            "locale_dir": server_conf.get("locale_dir"),
            "url": settings.public_url,
        },
        "logging": {
            "level": "DEBUG" if settings.debug else "WARNING"
        },
        "metadata": {
            "identification": {
                "title": identification_conf.get(
                    "title", {"en": "Potto"}
                ),
                "description": identification_conf.get(
                    "description", {"en": "The pygeoapi primate"}
                ),
                "keywords": identification_conf.get(
                    "keywords", {"en": ["geospatial", "data", "api"]}
                ),
                "keywords_type": identification_conf.get("keywords_type", "theme"),
                "terms_of_service": identification_conf.get(
                    "terms_of_service", "https://creativecommons.org/licenses/by/4.0/"),
                "url": identification_conf.get("url", "https://example.org"),
            },
            "license": {
                "name": license_conf.get("name", "CC-BY 4.0 license"),
                "url": license_conf.get("url", "https://creativecommons.org/licenses/by/4.0/"),
            },
            "provider": {
                "name": provider_conf.get("name", "Organization Name"),
                "url": provider_conf.get("url", "https://pygeoapi.io"),
            },
            "contact": {
                "name": contact_conf.get("name", "Lastname, Firstname"),
                "position": contact_conf.get("position", "Position Title"),
                "address": contact_conf.get("address", "Mailing Address"),
                "city": contact_conf.get("city", "City"),
                "stateorprovince": contact_conf.get("stateorprovince", "Administrative Area"),
                "postalcode": contact_conf.get("postalcode", "Zip or Postal Code"),
                "country": contact_conf.get("country", "Country"),
                "phone": contact_conf.get("phone", "+xx-xxx-xxx-xxxx"),
                "fax": contact_conf.get("fax", "+xx-xxx-xxx-xxxx"),
                "email": contact_conf.get("email", "you@example.org"),
                "url": contact_conf.get("url", "Contact URL"),
                "hours": contact_conf.get("hours", "Mo-Fr 08:00-17:00"),
                "instructions": contact_conf.get("instructions", "During hours of service. Off on weekends."),
                "role": contact_conf.get("role", "pointOfContact"),
            },
        },
        "resources": read_conf.get("resources", {}),
    }
