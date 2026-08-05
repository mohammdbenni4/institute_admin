"""FastAPI application factory.

``create_app`` builds and wires the ASGI application: configuration, logging,
middleware, exception handlers, routers and lifespan management. Keeping this in
a factory makes the app trivial to construct in tests with overridden settings.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from institute_administration.api.error_handlers import register_error_handlers
from institute_administration.api.rate_limit import (
    GENERAL,
    RateLimitExceededError,
    client_key,
    limiter,
    rate_limited_response,
)
from institute_administration.api.v1.router import api_router
from institute_administration.core.config import Settings, get_settings
from institute_administration.core.logging import configure_logging
from institute_administration.infrastructure.database.session import dispose_engine

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage start-up and shutdown of process-wide resources."""
    settings: Settings = app.state.settings
    logger.info("application.startup", environment=settings.environment.value)
    try:
        yield
    finally:
        await dispose_engine()
        logger.info("application.shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    @app.middleware("http")
    async def _general_rate_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Loose per-IP backstop. Auth endpoints add their own stricter rule.

        Middleware sits outside the exception handlers, so the refusal is built
        here rather than raised — a raised error would surface as a bare 500.
        """
        if request.method != "OPTIONS":
            try:
                limiter.check(client_key(request), GENERAL)
            except RateLimitExceededError as exc:
                return rate_limited_response(exc)
        return await call_next(request)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app
