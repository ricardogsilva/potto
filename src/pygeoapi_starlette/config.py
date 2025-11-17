from typing import NewType
from pathlib import Path

import pydantic_settings
from pygeoapi.util import yaml_load


ResourceName = NewType("ResourceName", str)


class PygeoapiStarletteSettings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="pygeoapi_starlette__",
        env_nested_delimiter="__",
        secrets_dir="/run/secrets",
    )

    bind_host: str = "127.0.0.1"
    bind_port: int = 3001
    debug: bool = False
    log_config_file: Path | None = None
    public_url: str = "http://localhost:3001"
    pygeoapi_config_file: Path = Path.home() / "pygeoapi-config.yml"
    templates_dir: Path | None = None
    translations_dir: Path | None = None
    locales: list[str] = ["en"]
    session_secret_key: str = "somesecretkey"
    static_dir: Path | None = None


def get_settings() -> PygeoapiStarletteSettings:
    return PygeoapiStarletteSettings()



def get_pygeoapi_settings(settings: PygeoapiStarletteSettings) -> dict:
    read_conf = yaml_load(settings.pygeoapi_config_file.read_text())
    server_conf = read_conf.get("server", {})
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
            "locale_dir": server_conf.get("locale_dir"),
            "url": settings.public_url,
        },
        "logging": {
            "level": "DEBUG" if settings.debug else "WARNING"
        },
        "metadata": {
            "identification": {
                "title": identification_conf.get(
                    "title", {"en": "pygeoapi default instance"}
                ),
                "description": identification_conf.get(
                    "description", {"en": "pygeoapi provides an API to geospatial data"}
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
