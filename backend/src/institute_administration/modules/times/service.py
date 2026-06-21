"""Times application layer: CRUD use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from institute_administration.modules.times.domain import (
    DaySchedule,
    Time,
    TimeNotFoundError,
    TimeRepository,
)
from institute_administration.shared.application.pagination import Page
from institute_administration.shared.application.sentinels import UNSET, Unset


@dataclass(frozen=True)
class CreateTimeInput:
    name: str
    days: DaySchedule = field(default_factory=dict)


@dataclass(frozen=True)
class UpdateTimeInput:
    name: str | Unset = UNSET
    # Only the days present here are changed; a value of ``None`` clears that day.
    days: DaySchedule = field(default_factory=dict)


class TimeService:
    def __init__(self, times: TimeRepository) -> None:
        self._times = times

    async def create(self, data: CreateTimeInput) -> Time:
        time = Time.create(name=data.name, days=data.days)
        await self._times.add(time)
        return await self.get(time.id)

    async def get(self, time_id: UUID) -> Time:
        time = await self._times.get_by_id(time_id)
        if time is None:
            raise TimeNotFoundError
        return time

    async def list(self, page: Page) -> tuple[list[Time], int]:
        return await self._times.list(page), await self._times.count()

    async def update(self, time_id: UUID, data: UpdateTimeInput) -> Time:
        time = await self.get(time_id)
        if data.name is not UNSET:
            time.rename(data.name)
        time.set_days(data.days)
        await self._times.update(time)
        return await self.get(time_id)

    async def delete(self, time_id: UUID) -> None:
        time = await self.get(time_id)
        await self._times.delete(time)
