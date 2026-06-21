"""Query side of CQRS.

A *query* requests data without changing state. A :class:`QueryHandler`
executes exactly one query type and returns a read model.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Query:
    """A request for data that does not mutate state."""


class QueryHandler[TQuery: Query, TResult](ABC):
    """Executes a single query type."""

    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        raise NotImplementedError
