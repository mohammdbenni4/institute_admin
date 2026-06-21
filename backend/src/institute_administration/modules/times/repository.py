"""Times infrastructure: SQLAlchemy repository implementation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.core.config import get_settings
from institute_administration.modules.times.domain import (
    WEEKDAYS,
    DaySchedule,
    Time,
    TimeRange,
    TimeRepository,
)
from institute_administration.modules.times.models import TimeModel
from institute_administration.shared.application.pagination import Page


def _range_to_json(time_range: TimeRange | None) -> dict[str, str] | None:
    if time_range is None:
        return None
    return {"from": time_range.start, "to": time_range.end}


def _range_from_json(value: dict[str, str] | None) -> TimeRange | None:
    if not value:
        return None
    return TimeRange(start=value["from"], end=value["to"])


def _to_entity(model: TimeModel) -> Time:
    days: DaySchedule = {day: _range_from_json(value) for day, value in model.day_values().items()}
    return Time(
        id=model.id,
        name=model.name,
        days=days,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply(model: TimeModel, time: Time) -> None:
    model.name = time.name
    for day in WEEKDAYS:
        setattr(model, day, _range_to_json(time.days[day]))


class SqlAlchemyTimeRepository(TimeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_collation = get_settings().arabic_collation

    async def add(self, time: Time) -> None:
        model = TimeModel(id=time.id)
        _apply(model, time)
        self._session.add(model)
        await self._session.flush()

    async def update(self, time: Time) -> None:
        model = await self._session.get(TimeModel, time.id)
        if model is None:  # pragma: no cover - guarded by the service layer
            return
        _apply(model, time)
        await self._session.flush()

    async def get_by_id(self, time_id: UUID) -> Time | None:
        model = await self._session.get(TimeModel, time_id)
        return _to_entity(model) if model else None

    async def list(self, page: Page) -> list[Time]:
        result = await self._session.execute(
            select(TimeModel)
            .order_by(TimeModel.name.collate(self._order_collation))
            .limit(page.limit)
            .offset(page.offset)
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(TimeModel))
        return int(result.scalar_one())

    async def delete(self, time: Time) -> None:
        model = await self._session.get(TimeModel, time.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
