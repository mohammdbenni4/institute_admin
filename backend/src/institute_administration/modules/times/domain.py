"""Times domain layer.

A ``Time`` aggregate is a weekly timetable: for each day of the week (Saturday
through Friday) it holds an optional :class:`TimeRange` (``from``/``to``). Days
with no session are ``None``.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from institute_administration.shared.application.pagination import Page
from institute_administration.shared.domain import (
    AggregateRoot,
    BusinessRuleViolationError,
    EntityNotFoundError,
    ValueObject,
)

# Week order used across the system (the Arabic/Hijri week starts on Saturday).
WEEKDAYS: tuple[str, ...] = (
    "saturday",
    "sunday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
)

_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# A schedule maps each weekday name to a time range or ``None``.
type DaySchedule = dict[str, "TimeRange | None"]


@dataclass(frozen=True, slots=True)
class TimeRange(ValueObject):
    """A start/end time range within a single day, as ``HH:MM`` strings."""

    start: str
    end: str

    def __post_init__(self) -> None:
        for value in (self.start, self.end):
            if not _HHMM.match(value):
                raise BusinessRuleViolationError("صيغة الوقت يجب أن تكون HH:MM")
        if self.start >= self.end:
            raise BusinessRuleViolationError("وقت البداية يجب أن يكون قبل وقت النهاية")


class Time(AggregateRoot[UUID]):
    """A weekly timetable referenced by halaqahs."""

    def __init__(
        self,
        *,
        id: UUID,
        name: str,
        days: DaySchedule | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        source = days or {}
        self.days: DaySchedule = {day: source.get(day) for day in WEEKDAYS}
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, *, name: str, days: DaySchedule | None = None) -> Time:
        return cls(id=uuid4(), name=name.strip(), days=days)

    def rename(self, name: str) -> None:
        self.name = name.strip()

    def set_days(self, changes: DaySchedule) -> None:
        """Replace the schedule for the provided days only (partial update)."""
        for day, value in changes.items():
            if day not in self.days:
                raise BusinessRuleViolationError(f"يوم غير معروف: {day}")
            self.days[day] = value


class TimeRepository(ABC):
    @abstractmethod
    async def add(self, time: Time) -> None: ...

    @abstractmethod
    async def update(self, time: Time) -> None: ...

    @abstractmethod
    async def get_by_id(self, time_id: UUID) -> Time | None: ...

    @abstractmethod
    async def list(self, page: Page) -> list[Time]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def delete(self, time: Time) -> None: ...


class TimeNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "الوقت غير موجود") -> None:
        super().__init__(message)
