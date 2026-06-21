"""Shared application primitives (use-case orchestration building blocks)."""

from institute_administration.shared.application.command import Command, CommandHandler
from institute_administration.shared.application.exceptions import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
)
from institute_administration.shared.application.query import Query, QueryHandler
from institute_administration.shared.application.unit_of_work import UnitOfWork

__all__ = [
    "ApplicationError",
    "AuthenticationError",
    "AuthorizationError",
    "Command",
    "CommandHandler",
    "Query",
    "QueryHandler",
    "UnitOfWork",
]
