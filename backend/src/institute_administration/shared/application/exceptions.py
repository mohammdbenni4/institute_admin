"""Application-level exceptions (use-case orchestration failures)."""

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for errors raised by the application layer."""


class AuthenticationError(ApplicationError):
    """Raised when the actor's identity cannot be established (invalid credentials/token)."""


class AuthorizationError(ApplicationError):
    """Raised when the current actor is not allowed to perform an action."""
