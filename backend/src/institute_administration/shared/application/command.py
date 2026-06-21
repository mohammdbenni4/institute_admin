"""Command side of CQRS.

A *command* expresses an intent to change state. A :class:`CommandHandler`
executes exactly one command type and returns its result.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """An intent to change the state of the system."""


class CommandHandler[TCommand: Command, TResult](ABC):
    """Executes a single command type."""

    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        raise NotImplementedError
