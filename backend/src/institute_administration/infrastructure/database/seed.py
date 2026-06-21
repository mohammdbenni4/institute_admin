"""Idempotent database seeding.

Creates the bootstrap super-admin account from settings if it does not already
exist. Run via ``make seed`` or the ``institute-admin-seed`` console script.
"""

from __future__ import annotations

import asyncio

import structlog

from institute_administration.core.config import get_settings
from institute_administration.core.security import hash_password
from institute_administration.infrastructure.database.session import (
    dispose_engine,
    get_session_factory,
)
from institute_administration.modules.identity.domain import User, UserRole
from institute_administration.modules.identity.repository import SqlAlchemyUserRepository

logger = structlog.get_logger(__name__)


async def seed_super_admin() -> None:
    """Create the configured super-admin user if it does not exist."""
    settings = get_settings()
    session_factory = get_session_factory()

    async with session_factory() as session:
        repository = SqlAlchemyUserRepository(session)
        existing = await repository.get_by_email(settings.superadmin_email)
        if existing is not None:
            logger.info("seed.super_admin.exists", email=existing.email.value)
            return

        user = User.create(
            full_name=settings.superadmin_full_name,
            email=settings.superadmin_email,
            password_hash=hash_password(settings.superadmin_password),
            role=UserRole.SUPER_ADMIN,
        )
        await repository.add(user)
        await session.commit()
        logger.info("seed.super_admin.created", email=user.email.value)


async def _run() -> None:
    try:
        await seed_super_admin()
    finally:
        await dispose_engine()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
