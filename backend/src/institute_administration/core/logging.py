"""Structured logging configuration based on ``structlog``.

Call :func:`configure_logging` once during application start-up. Afterwards,
obtain loggers anywhere with ``structlog.get_logger(__name__)``.
"""

from __future__ import annotations

import logging

import structlog

from institute_administration.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure the standard library and structlog loggers."""
    log_level = logging.getLevelName(settings.log_level.value)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[*shared_processors, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route the stdlib root logger (uvicorn, sqlalchemy, ...) at the same level.
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        force=True,
    )
