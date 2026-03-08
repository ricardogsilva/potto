"""FastAPI app for serving non-HTML responses.

NOTE: We do not use any lifespan-related functionality when setting up this
FastAPI application because the way that it gets used at runtime is by being
mounted by our main starlette-based app. Therefore, lifespan is configured
in the starlette app.
"""

from fastapi import FastAPI

from ... import config

from .routers import (
    base,
    collections,
    items,
)


def create_api_app() -> FastAPI:
    settings = config.get_settings()
    return create_api_app_from_settings(settings)


def create_api_app_from_settings(settings: config.PottoSettings) -> FastAPI:
    app = FastAPI(
        title="Potto",
        summary="OGC API server",
    )
    app.include_router(collections.router)
    app.include_router(items.router)
    app.include_router(base.router)
    return app