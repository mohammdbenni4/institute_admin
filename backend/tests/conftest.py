"""Shared pytest fixtures.

The ``client`` fixture builds the app with test settings and drives it through
an ASGI transport with a managed lifespan — no network socket required.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from institute_administration.api.app import create_app
from institute_administration.core.config import Environment, Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(environment=Environment.TEST, debug=True)


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
            yield http_client
