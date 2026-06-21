"""Unit of Work abstraction.

The Unit of Work defines an atomic boundary around a use case: either all
changes within it are persisted, or none are. The application layer depends on
this interface only; the infrastructure layer provides a concrete, database-
backed implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class UnitOfWork(ABC):
    """Atomic transactional boundary for a use case."""

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    @abstractmethod
    async def commit(self) -> None:
        """Persist all changes made within the unit of work."""
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        """Discard all changes made within the unit of work."""
        raise NotImplementedError
