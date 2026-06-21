"""Unit tests for the shared domain kernel."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from institute_administration.shared.domain import AggregateRoot, DomainEvent, Entity, ValueObject


class _User(Entity[int]):
    def __init__(self, entity_id: int, name: str) -> None:
        super().__init__(entity_id)
        self.name = name


@dataclass(frozen=True, slots=True)
class _Email(ValueObject):
    value: str


@dataclass(frozen=True, kw_only=True)
class _UserRegistered(DomainEvent):
    user_id: int


class _Account(AggregateRoot[int]):
    pass


pytestmark = pytest.mark.unit


def test_entity_equality_is_identity_based() -> None:
    assert _User(1, "a") == _User(1, "b")
    assert _User(1, "a") != _User(2, "a")
    assert _User(1, "a") != object()


def test_entity_is_hashable_by_identity() -> None:
    assert len({_User(1, "a"), _User(1, "b")}) == 1


def test_value_object_equality_is_attribute_based() -> None:
    assert _Email("a@b.com") == _Email("a@b.com")
    assert _Email("a@b.com") != _Email("x@y.com")


def test_aggregate_records_and_pulls_events() -> None:
    account = _Account(1)
    account.record_event(_UserRegistered(user_id=1))

    events = account.pull_domain_events()

    assert len(events) == 1
    assert isinstance(events[0], _UserRegistered)
    assert account.pull_domain_events() == []
