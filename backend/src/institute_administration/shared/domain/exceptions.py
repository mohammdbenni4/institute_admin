"""Domain-level exceptions.

These represent violations of business rules and are independent of any
delivery mechanism (HTTP, CLI, ...). The API layer translates them into
appropriate transport responses.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain errors."""


class BusinessRuleViolationError(DomainError):
    """Raised when an invariant or business rule is violated."""


class EntityNotFoundError(DomainError):
    """Raised when a requested entity does not exist."""


class ConflictError(DomainError):
    """Raised when an operation conflicts with existing state (e.g. duplicates)."""
