"""Base class for aggregate roots.

An aggregate root is the entry point to a cluster of objects that are treated
as a single unit for data changes. It is the only member of the aggregate that
outside objects may hold a reference to, and it is responsible for recording the
domain events that result from changes to its state.
"""

from __future__ import annotations

from institute_administration.shared.domain.domain_event import DomainEvent
from institute_administration.shared.domain.entity import Entity


class AggregateRoot[EntityIdT](Entity[EntityIdT]):
    """Consistency boundary that records the domain events it produces."""

    def __init__(self, entity_id: EntityIdT) -> None:
        super().__init__(entity_id)
        self._domain_events: list[DomainEvent] = []

    def record_event(self, event: DomainEvent) -> None:
        """Register a domain event to be published after persistence."""
        self._domain_events.append(event)

    def pull_domain_events(self) -> list[DomainEvent]:
        """Return and clear the recorded events (typically by the unit of work)."""
        events = list(self._domain_events)
        self._domain_events.clear()
        return events
