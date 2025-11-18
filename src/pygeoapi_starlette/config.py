from pathlib import Path

import pydantic_settings


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
