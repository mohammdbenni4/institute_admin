"""Analytics infrastructure: one windowed read over the daily records.

A single query joins each daily record with its student and halaqah names; the
service layer derives every metric from the returned rows in Python (the row
count for one month at institute scale is small and bounded).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.modules.daily_records.models import DailyRecordModel
from institute_administration.modules.halaqahs.models import HalaqahModel
from institute_administration.modules.students.models import StudentModel


@dataclass(frozen=True)
class PeriodRow:
    """One daily record flattened with display names, for aggregation."""

    halaqah_id: UUID
    halaqah_name: str
    student_id: UUID
    student_name: str
    present: bool
    total_points: int
    record_date: date


class SqlAlchemyAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def rows_in_period(
        self, date_from: date, date_to: date, halaqah_ids: frozenset[UUID] | None = None
    ) -> list[PeriodRow]:
        stmt = (
            select(
                DailyRecordModel.halaqah_id,
                HalaqahModel.name,
                DailyRecordModel.student_id,
                StudentModel.full_name,
                DailyRecordModel.present,
                DailyRecordModel.total_points,
                DailyRecordModel.record_date,
            )
            .join(StudentModel, DailyRecordModel.student_id == StudentModel.id)
            .join(HalaqahModel, DailyRecordModel.halaqah_id == HalaqahModel.id)
            .where(DailyRecordModel.record_date >= date_from)
            .where(DailyRecordModel.record_date <= date_to)
            .order_by(DailyRecordModel.record_date)
        )
        if halaqah_ids is not None:
            stmt = stmt.where(DailyRecordModel.halaqah_id.in_(halaqah_ids))
        result = await self._session.execute(stmt)
        return [
            PeriodRow(
                halaqah_id=row[0],
                halaqah_name=row[1],
                student_id=row[2],
                student_name=row[3],
                present=row[4],
                total_points=row[5],
                record_date=row[6],
            )
            for row in result.all()
        ]
