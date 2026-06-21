"""Shared domain primitives."""

from institute_administration.shared.domain.aggregate_root import AggregateRoot
from institute_administration.shared.domain.domain_event import DomainEvent
from institute_administration.shared.domain.entity import Entity
from institute_administration.shared.domain.exceptions import (
    BusinessRuleViolationError,
    ConflictError,
    DomainError,
    EntityNotFoundError,
)
from institute_administration.shared.domain.value_object import ValueObject

__all__ = [
    "AggregateRoot",
    "BusinessRuleViolationError",
    "ConflictError",
    "DomainError",
    "DomainEvent",
    "Entity",
    "EntityNotFoundError",
    "ValueObject",
]
