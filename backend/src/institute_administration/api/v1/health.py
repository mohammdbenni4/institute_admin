"""Operational health endpoints.

* ``/health``    — liveness: the process is up and serving requests.
* ``/health/ready`` — readiness: dependencies (the database) are reachable.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from institute_administration.api.dependencies import DbSession

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthStatus, summary="Liveness probe")
async def health() -> HealthStatus:
    """Return ``ok`` if the application process is running."""
    from institute_administration import __version__

    return HealthStatus(status="ok", version=__version__)


@router.get("/health/ready", summary="Readiness probe")
async def readiness(session: DbSession) -> JSONResponse:
    """Return ``ready`` only if the database responds to a trivial query."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # any failure means "not ready"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "database": "unavailable"},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ready", "database": "ok"},
    )
