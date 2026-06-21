"""Times presentation layer: Pydantic schemas.

The wire format uses ``from``/``to`` keys per day (as requested); the domain
uses :class:`TimeRange(start, end)`. This module translates between them.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from institute_administration.modules.times.domain import WEEKDAYS, Time, TimeRange

_HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


class DayTimeSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    from_: str = Field(alias="from", pattern=_HHMM, examples=["16:00"])
    to: str = Field(pattern=_HHMM, examples=["18:00"])

    def to_range(self) -> TimeRange:
        return TimeRange(start=self.from_, end=self.to)

    @classmethod
    def from_range(cls, time_range: TimeRange | None) -> DayTimeSchema | None:
        if time_range is None:
            return None
        return cls(from_=time_range.start, to=time_range.end)


class TimeResponse(BaseModel):
    id: UUID
    name: str
    saturday: DayTimeSchema | None
    sunday: DayTimeSchema | None
    monday: DayTimeSchema | None
    tuesday: DayTimeSchema | None
    wednesday: DayTimeSchema | None
    thursday: DayTimeSchema | None
    friday: DayTimeSchema | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, time: Time) -> TimeResponse:
        days = {day: DayTimeSchema.from_range(time.days[day]) for day in WEEKDAYS}
        return cls(
            id=time.id,
            name=time.name,
            created_at=time.created_at,
            updated_at=time.updated_at,
            **days,
        )


class TimeListResponse(BaseModel):
    items: list[TimeResponse]
    total: int
    limit: int
    offset: int


class _TimeDaysRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    saturday: DayTimeSchema | None = None
    sunday: DayTimeSchema | None = None
    monday: DayTimeSchema | None = None
    tuesday: DayTimeSchema | None = None
    wednesday: DayTimeSchema | None = None
    thursday: DayTimeSchema | None = None
    friday: DayTimeSchema | None = None


class TimeCreateRequest(_TimeDaysRequest):
    name: str = Field(min_length=1, max_length=150)


class TimeUpdateRequest(_TimeDaysRequest):
    """Partial update: only the fields/days present in the request are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
