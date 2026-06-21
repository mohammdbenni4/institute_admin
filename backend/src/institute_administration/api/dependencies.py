"""Shared FastAPI dependencies.

These provide request-scoped access to infrastructure (database sessions, units
of work). Endpoints and application services receive them via ``Depends`` so
that wiring stays explicit and testable.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.infrastructure.database.session import get_session_factory
from institute_administration.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped, transactional database session.

    This is the per-request unit of work: the session is committed when the
    request handler returns successfully, and rolled back if it raises. Services
    may ``flush()`` to surface constraint violations early and map them to
    domain errors.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_unit_of_work() -> SqlAlchemyUnitOfWork:
    """Return a unit of work bound to the session factory.

    Use as ``async with uow: ...`` inside an application service.
    """
    return SqlAlchemyUnitOfWork(get_session_factory())


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
UnitOfWorkDep = Annotated[SqlAlchemyUnitOfWork, Depends(get_unit_of_work)]
