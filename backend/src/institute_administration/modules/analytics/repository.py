"""Analytics infrastructure: one windowed read over the daily records.

A single query joins each daily record with its student and halaqah names; the
service layer derives every metric from the returned rows in Python (the row
count for one month at institute scale is small and bounded).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.modules.daily_records.models import DailyRecordModel
from institute_administration.modules.halaqahs.models import HalaqahModel
from institute_administration.modules.identity.models import UserModel
from institute_administration.modules.students.models import StudentModel
from institute_administration.modules.teachers.models import TeacherModel
from institute_administration.shared.application.pagination import Page


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


@dataclass(frozen=True)
class AttendanceRow:
    """One student's month of attendance, already aggregated by the database."""

    student_id: UUID
    student_name: str
    father_number: str | None
    halaqah_id: UUID | None
    halaqah_name: str | None
    teacher_id: UUID | None
    teacher_name: str | None
    present: int  # every attended day, late ones included
    late: int  # subset of `present`
    absent: int
    excused: int
    total: int


@dataclass(frozen=True)
class AttendanceTotals:
    """Totals across the whole filtered set, not just the returned page."""

    students: int
    present: int
    late: int
    absent: int
    excused: int
    rate_sum: int


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

    # ---------------------------------------------------------- attendance matrix --
    #
    # The admin attendance page used to page the raw daily-records endpoint 200 rows
    # at a time (a month of a mid-size institute is thousands of rows, i.e. dozens of
    # sequential requests) and then aggregate in the browser. Everything below is
    # aggregated, filtered, sorted and paginated by Postgres instead, so the page
    # fetches exactly the rows it draws.

    def _matrix_base(
        self,
        date_from: date,
        date_to: date,
        *,
        halaqah_id: UUID | None,
        teacher_id: UUID | None,
        search: str | None,
        halaqah_ids: frozenset[UUID] | None,
        on_day: date | None,
    ) -> Select[Any]:
        """Per-student attendance counts for the window, before sort/paging."""
        window = and_(
            DailyRecordModel.student_id == StudentModel.id,
            DailyRecordModel.record_date >= date_from,
            DailyRecordModel.record_date <= date_to,
        )
        if on_day is not None:
            # When a single day is selected, the counters describe that day only.
            window = and_(window, DailyRecordModel.record_date == on_day)

        stmt = (
            select(
                StudentModel.id,
                StudentModel.full_name,
                StudentModel.father_number,
                HalaqahModel.id,
                HalaqahModel.name,
                TeacherModel.id,
                UserModel.full_name,
                func.count(DailyRecordModel.id)
                .filter(DailyRecordModel.present.is_(True))
                .label("present"),
                func.count(DailyRecordModel.id)
                .filter(DailyRecordModel.late.is_(True))
                .label("late"),
                func.count(DailyRecordModel.id)
                .filter(
                    and_(
                        DailyRecordModel.present.is_(False),
                        DailyRecordModel.excused.is_(False),
                    )
                )
                .label("absent"),
                func.count(DailyRecordModel.id)
                .filter(
                    and_(
                        DailyRecordModel.present.is_(False),
                        DailyRecordModel.excused.is_(True),
                    )
                )
                .label("excused"),
                func.count(DailyRecordModel.id).label("total"),
            )
            .select_from(StudentModel)
            .outerjoin(HalaqahModel, StudentModel.halaqah_id == HalaqahModel.id)
            .outerjoin(TeacherModel, HalaqahModel.teacher_id == TeacherModel.id)
            .outerjoin(UserModel, TeacherModel.user_id == UserModel.id)
            .outerjoin(DailyRecordModel, window)
            .group_by(
                StudentModel.id,
                StudentModel.full_name,
                StudentModel.father_number,
                HalaqahModel.id,
                HalaqahModel.name,
                TeacherModel.id,
                UserModel.full_name,
            )
        )
        if halaqah_id is not None:
            stmt = stmt.where(StudentModel.halaqah_id == halaqah_id)
        if teacher_id is not None:
            stmt = stmt.where(HalaqahModel.teacher_id == teacher_id)
        if halaqah_ids is not None:
            stmt = stmt.where(StudentModel.halaqah_id.in_(halaqah_ids))
        if search:
            stmt = stmt.where(StudentModel.full_name.ilike(f"%{search}%"))
        return stmt

    @staticmethod
    def _status_having(status: str | None) -> Any:
        """Keep only students that recorded the requested status in the window."""
        if status == "present":
            return func.count(DailyRecordModel.id).filter(DailyRecordModel.present.is_(True)) > 0
        if status == "late":
            return func.count(DailyRecordModel.id).filter(DailyRecordModel.late.is_(True)) > 0
        if status == "excused":
            return (
                func.count(DailyRecordModel.id).filter(
                    and_(
                        DailyRecordModel.present.is_(False),
                        DailyRecordModel.excused.is_(True),
                    )
                )
                > 0
            )
        if status == "absent":
            return (
                func.count(DailyRecordModel.id).filter(
                    and_(
                        DailyRecordModel.present.is_(False),
                        DailyRecordModel.excused.is_(False),
                    )
                )
                > 0
            )
        return None

    async def attendance_page(
        self,
        date_from: date,
        date_to: date,
        *,
        page: Page,
        halaqah_id: UUID | None = None,
        teacher_id: UUID | None = None,
        search: str | None = None,
        status: str | None = None,
        on_day: date | None = None,
        sort: str = "halaqah",
        halaqah_ids: frozenset[UUID] | None = None,
        order_collation: str | None = None,
    ) -> list[AttendanceRow]:
        stmt = self._matrix_base(
            date_from,
            date_to,
            halaqah_id=halaqah_id,
            teacher_id=teacher_id,
            search=search,
            halaqah_ids=halaqah_ids,
            on_day=on_day,
        )
        having = self._status_having(status)
        if having is not None:
            stmt = stmt.having(having)

        present = func.count(DailyRecordModel.id).filter(DailyRecordModel.present.is_(True))
        total = func.count(DailyRecordModel.id)
        # Attendance rate as an integer percentage; a student with no record sorts at 0.
        rate = case((total > 0, present * 100 / total), else_=0)

        # Arabic names need the institute's collation to sort the way readers expect.
        # (`Any` because a collated column and a plain one have unrelated static types.)
        name: Any = StudentModel.full_name
        halaqah_name: Any = HalaqahModel.name
        if order_collation:
            name = name.collate(order_collation)
            halaqah_name = halaqah_name.collate(order_collation)

        if sort == "name":
            stmt = stmt.order_by(name)
        elif sort == "rate-asc":
            stmt = stmt.order_by(rate.asc(), name)
        elif sort == "rate-desc":
            stmt = stmt.order_by(rate.desc(), name)
        else:
            stmt = stmt.order_by(halaqah_name.nulls_last(), name)

        result = await self._session.execute(stmt.limit(page.limit).offset(page.offset))
        return [
            AttendanceRow(
                student_id=row[0],
                student_name=row[1],
                father_number=row[2],
                halaqah_id=row[3],
                halaqah_name=row[4],
                teacher_id=row[5],
                teacher_name=row[6],
                present=row[7],
                late=row[8],
                absent=row[9],
                excused=row[10],
                total=row[11],
            )
            for row in result.all()
        ]

    async def attendance_totals(
        self,
        date_from: date,
        date_to: date,
        *,
        halaqah_id: UUID | None = None,
        teacher_id: UUID | None = None,
        search: str | None = None,
        status: str | None = None,
        on_day: date | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
    ) -> AttendanceTotals:
        """Summary over the whole filtered set — the KPI cards must not describe
        only the page currently on screen."""
        inner = self._matrix_base(
            date_from,
            date_to,
            halaqah_id=halaqah_id,
            teacher_id=teacher_id,
            search=search,
            halaqah_ids=halaqah_ids,
            on_day=on_day,
        )
        having = self._status_having(status)
        if having is not None:
            inner = inner.having(having)
        sub = inner.subquery()

        rate = case((sub.c.total > 0, sub.c.present * 100 / sub.c.total), else_=0)
        stmt = select(
            func.count(),
            func.coalesce(func.sum(sub.c.present), 0),
            func.coalesce(func.sum(sub.c.late), 0),
            func.coalesce(func.sum(sub.c.absent), 0),
            func.coalesce(func.sum(sub.c.excused), 0),
            func.coalesce(func.sum(rate), 0),
        ).select_from(sub)
        row = (await self._session.execute(stmt)).one()
        return AttendanceTotals(
            students=int(row[0]),
            present=int(row[1]),
            late=int(row[2]),
            absent=int(row[3]),
            excused=int(row[4]),
            rate_sum=int(row[5]),
        )

    async def attendance_days(
        self, student_ids: Sequence[UUID], date_from: date, date_to: date
    ) -> dict[UUID, dict[date, str]]:
        """Day-by-day status for the students actually on screen.

        Bounded by the page size (about 50 students by 31 days), which is why the whole
        month no longer has to travel to the browser.
        """
        if not student_ids:
            return {}
        stmt = select(
            DailyRecordModel.student_id,
            DailyRecordModel.record_date,
            DailyRecordModel.present,
            DailyRecordModel.excused,
            DailyRecordModel.late,
        ).where(
            DailyRecordModel.student_id.in_(student_ids),
            DailyRecordModel.record_date >= date_from,
            DailyRecordModel.record_date <= date_to,
        )
        out: dict[UUID, dict[date, str]] = {sid: {} for sid in student_ids}
        for row in await self._session.execute(stmt):
            # `L` takes precedence over `P` so lateness is visible on the heat-map;
            # a late day still counts as attended in the `present` total.
            attended = "L" if row.late else "P"
            absent = "E" if row.excused else "A"
            status = attended if row.present else absent
            out[row.student_id][row.record_date] = status
        return out
