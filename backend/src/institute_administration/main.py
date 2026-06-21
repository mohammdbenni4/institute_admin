"""Application entry point.

``app`` is the ASGI application discovered by uvicorn/gunicorn. ``main`` runs a
development server and backs the ``institute-admin-api`` console script.
"""

from __future__ import annotations

import uvicorn

from institute_administration.api.app import create_app
from institute_administration.core.config import get_settings

app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "institute_administration.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
