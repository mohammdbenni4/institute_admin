"""Analytics application layer: derive KPIs, leaderboards and the watch-list."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from institute_administration.modules.analytics.repository import (
    AttendanceRow,
    SqlAlchemyAnalyticsRepository,
)
from institute_administration.shared.application.pagination import Page

# At-risk thresholds.
_ABSENCE_THRESHOLD = 2
_DECLINE_MIN_SESSIONS = 4
_DECLINE_RATIO = 0.8


@dataclass(frozen=True)
class AttendanceStudent:
    """One row of the attendance matrix: totals plus a packed per-day string."""

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
    rate: int
    # One character per day of the window: P present, L late, A absent, E excused,
    # '.' no record. A month costs ~31 bytes per student instead of a JSON object
    # per record.
    days: str


@dataclass(frozen=True)
class AttendanceMatrix:
    date_from: date
    date_to: date
    days: int
    items: list[AttendanceStudent]
    total: int
    limit: int
    offset: int
    # Summary over every matching student, not only this page.
    students: int
    total_present: int
    total_late: int
    total_absent: int
    total_excused: int
    average_rate: int


@dataclass(frozen=True)
class Overview:
    records: int
    present: int
    absent: int
    attendance_rate: float
    total_points: int
    active_students: int
    halaqahs: int


@dataclass(frozen=True)
class LeaderboardEntry:
    rank: int
    student_id: UUID
    student_name: str
    total_points: int
    sessions: int
    present_count: int


@dataclass(frozen=True)
class HalaqahLeaderboard:
    halaqah_id: UUID
    halaqah_name: str
    students: list[LeaderboardEntry] = field(default_factory=list)


@dataclass(frozen=True)
class AtRiskStudent:
    student_id: UUID
    student_name: str
    halaqah_id: UUID
    halaqah_name: str
    sessions: int
    absences: int
    total_points: int
    reasons: list[str]


class AnalyticsService:
    def __init__(self, repository: SqlAlchemyAnalyticsRepository) -> None:
        self._repository = repository

    async def attendance_matrix(
        self,
        date_from: date,
        date_to: date,
        *,
        limit: int,
        offset: int,
        halaqah_id: UUID | None = None,
        teacher_id: UUID | None = None,
        search: str | None = None,
        status: str | None = None,
        on_day: date | None = None,
        sort: str = "halaqah",
        halaqah_ids: frozenset[UUID] | None = None,
        order_collation: str | None = None,
    ) -> AttendanceMatrix:
        """The admin attendance heat-map, aggregated and paginated by the database.

        Three bounded queries (page, totals, day details for the page) replace what
        used to be dozens of sequential `/daily-records` calls plus a full in-browser
        aggregation of every record in the month.
        """
        filters: dict[str, Any] = {
            "halaqah_id": halaqah_id,
            "teacher_id": teacher_id,
            "search": search,
            "status": status,
            "on_day": on_day,
            "halaqah_ids": halaqah_ids,
        }
        rows = await self._repository.attendance_page(
            date_from,
            date_to,
            page=Page(limit=limit, offset=offset),
            sort=sort,
            order_collation=order_collation,
            **filters,
        )
        totals = await self._repository.attendance_totals(date_from, date_to, **filters)
        by_day = await self._repository.attendance_days(
            [r.student_id for r in rows], date_from, date_to
        )

        span = (date_to - date_from).days + 1
        items = [
            self._to_student(row, by_day.get(row.student_id, {}), date_from, span) for row in rows
        ]
        return AttendanceMatrix(
            date_from=date_from,
            date_to=date_to,
            days=span,
            items=items,
            total=totals.students,
            limit=limit,
            offset=offset,
            students=totals.students,
            total_present=totals.present,
            total_late=totals.late,
            total_absent=totals.absent,
            total_excused=totals.excused,
            average_rate=round(totals.rate_sum / totals.students) if totals.students else 0,
        )

    @staticmethod
    def _to_student(
        row: AttendanceRow, statuses: dict[date, str], date_from: date, span: int
    ) -> AttendanceStudent:
        days = "".join(statuses.get(date_from + timedelta(days=i), ".") for i in range(span))
        return AttendanceStudent(
            student_id=row.student_id,
            student_name=row.student_name,
            father_number=row.father_number,
            halaqah_id=row.halaqah_id,
            halaqah_name=row.halaqah_name,
            teacher_id=row.teacher_id,
            teacher_name=row.teacher_name,
            present=row.present,
            late=row.late,
            absent=row.absent,
            excused=row.excused,
            total=row.total,
            rate=round(row.present * 100 / row.total) if row.total else 0,
            days=days,
        )

    async def overview(
        self, date_from: date, date_to: date, halaqah_ids: frozenset[UUID] | None = None
    ) -> Overview:
        rows = await self._repository.rows_in_period(date_from, date_to, halaqah_ids)
        records = len(rows)
        present = sum(1 for r in rows if r.present)
        total_points = sum(r.total_points for r in rows)
        return Overview(
            records=records,
            present=present,
            absent=records - present,
            attendance_rate=round(present / records, 4) if records else 0.0,
            total_points=total_points,
            active_students=len({r.student_id for r in rows}),
            halaqahs=len({r.halaqah_id for r in rows}),
        )

    async def halaqah_leaderboard(
        self,
        date_from: date,
        date_to: date,
        top: int,
        halaqah_ids: frozenset[UUID] | None = None,
    ) -> list[HalaqahLeaderboard]:
        rows = await self._repository.rows_in_period(date_from, date_to, halaqah_ids)
        halaqahs: dict[UUID, dict[str, Any]] = {}
        for r in rows:
            h = halaqahs.setdefault(r.halaqah_id, {"name": r.halaqah_name, "students": {}})
            s = h["students"].setdefault(
                r.student_id, {"name": r.student_name, "points": 0, "sessions": 0, "present": 0}
            )
            s["points"] += r.total_points
            s["sessions"] += 1
            s["present"] += 1 if r.present else 0

        boards: list[HalaqahLeaderboard] = []
        for hid, h in halaqahs.items():
            ranked = sorted(
                h["students"].items(), key=lambda kv: (-kv[1]["points"], kv[1]["name"])
            )[:top]
            entries = [
                LeaderboardEntry(
                    rank=i + 1,
                    student_id=sid,
                    student_name=sv["name"],
                    total_points=sv["points"],
                    sessions=sv["sessions"],
                    present_count=sv["present"],
                )
                for i, (sid, sv) in enumerate(ranked)
            ]
            boards.append(HalaqahLeaderboard(hid, h["name"], entries))
        boards.sort(key=lambda b: b.halaqah_name)
        return boards

    async def at_risk(
        self, date_from: date, date_to: date, halaqah_ids: frozenset[UUID] | None = None
    ) -> list[AtRiskStudent]:
        rows = await self._repository.rows_in_period(date_from, date_to, halaqah_ids)
        students: dict[UUID, dict[str, Any]] = {}
        for r in rows:
            a = students.setdefault(
                r.student_id,
                {
                    "name": r.student_name,
                    "halaqah_id": r.halaqah_id,
                    "halaqah_name": r.halaqah_name,
                    "recs": [],
                },
            )
            a["recs"].append((r.record_date, r.present, r.total_points))

        flagged: list[AtRiskStudent] = []
        for sid, a in students.items():
            recs = sorted(a["recs"], key=lambda t: t[0])
            sessions = len(recs)
            absences = sum(1 for _, present, _ in recs if not present)
            total = sum(points for _, _, points in recs)
            reasons: list[str] = []
            if absences >= _ABSENCE_THRESHOLD:
                reasons.append(f"غياب متكرر ({absences} مرات)")
            present_points = [points for _, present, points in recs if present]
            if len(present_points) >= _DECLINE_MIN_SESSIONS:
                half = len(present_points) // 2
                first = present_points[:half]
                second = present_points[half:]
                avg_first = sum(first) / len(first)
                avg_second = sum(second) / len(second)
                if avg_first > 0 and avg_second < avg_first * _DECLINE_RATIO:
                    reasons.append("تراجع في الأداء")
            if reasons:
                flagged.append(
                    AtRiskStudent(
                        student_id=sid,
                        student_name=a["name"],
                        halaqah_id=a["halaqah_id"],
                        halaqah_name=a["halaqah_name"],
                        sessions=sessions,
                        absences=absences,
                        total_points=total,
                        reasons=reasons,
                    )
                )
        flagged.sort(key=lambda s: (-s.absences, s.total_points))
        return flagged
