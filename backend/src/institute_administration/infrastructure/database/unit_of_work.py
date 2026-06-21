"""SQLAlchemy-backed Unit of Work.

Wraps an :class:`AsyncSession` in the application's :class:`UnitOfWork`
contract. Repositories are constructed against ``self.session`` so that all
work performed inside the context manager shares a single transaction.
"""

from __future__ import annotations

from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from institute_administration.shared.application.unit_of_work import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Database-backed unit of work using a single ``AsyncSession``."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:  # pragma: no cover - guard
            raise RuntimeError("UnitOfWork must be entered before accessing the session")
        return self._session

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        # Instantiate per-context repositories here once modules exist, e.g.:
        #   self.surahs = SqlAlchemySurahRepository(self._session)
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:  # type: ignore[no-untyped-def]
        try:
            await super().__aexit__(exc_type, exc, traceback)
        finally:
            if self._session is not None:
                await self._session.close()
                self._session = None

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
