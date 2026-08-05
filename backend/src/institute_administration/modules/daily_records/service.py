"""Daily records application layer: CRUD use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from institute_administration.modules.daily_records.domain import (
    DEFAULT_SCORING,
    DailyRecord,
    DailyRecordNotFoundError,
    DailyRecordRepository,
    ScoringPolicy,
)
from institute_administration.shared.application.pagination import Page
from institute_administration.shared.application.sentinels import UNSET, Unset


def _as_decimal(value: Decimal | float | None) -> Decimal | None:
    """Page counts are stored as Decimal; `str()` first so 0.1 does not become
    0.1000000000000000055511151231257827."""
    return Decimal(str(value)) if value is not None else None


@dataclass(frozen=True)
class CreateDailyRecordInput:
    student_id: UUID
    teacher_id: UUID
    halaqah_id: UUID
    present: bool
    excused: bool = False
    late: bool = False
    excuse_reason: str | None = None
    record_date: date | None = None
    exam_from: int | None = None
    exam_to: int | None = None
    exam_total: Decimal | float | None = None
    homework: str | None = None
    problems: str | None = None
    rating: int | None = None
    revision_lesson: str | None = None
    revision_rating: int | None = None
    attitude: int | None = None
    added_points: int = 0
    notes: str | None = None
    problem_ids: list[UUID] = field(default_factory=list)


@dataclass(frozen=True)
class UpdateDailyRecordInput:
    teacher_id: UUID | Unset = UNSET
    halaqah_id: UUID | Unset = UNSET
    record_date: date | Unset = UNSET
    present: bool | Unset = UNSET
    excused: bool | Unset = UNSET
    late: bool | Unset = UNSET
    excuse_reason: str | None | Unset = UNSET
    exam_from: int | None | Unset = UNSET
    exam_to: int | None | Unset = UNSET
    exam_total: Decimal | float | None | Unset = UNSET
    homework: str | None | Unset = UNSET
    problems: str | None | Unset = UNSET
    rating: int | None | Unset = UNSET
    revision_lesson: str | None | Unset = UNSET
    revision_rating: int | None | Unset = UNSET
    attitude: int | None | Unset = UNSET
    added_points: int | Unset = UNSET
    notes: str | None | Unset = UNSET
    problem_ids: list[UUID] | Unset = UNSET


@dataclass(frozen=True)
class BulkAttendanceEntry:
    student_id: UUID
    present: bool
    excused: bool = False
    late: bool = False
    excuse_reason: str | None = None


@dataclass(frozen=True)
class UpsertDailyRecordEntry:
    """One record identified by its natural key ``(student_id, record_date)``.

    The offline client never learns the server id of a record it created, so the
    bulk upsert matches on this key instead. Every assessment field is sent, which
    makes the write a full overwrite (last-write-wins).
    """

    student_id: UUID
    record_date: date
    present: bool = True
    excused: bool = False
    late: bool = False
    excuse_reason: str | None = None
    exam_from: int | None = None
    exam_to: int | None = None
    exam_total: Decimal | float | None = None
    homework: str | None = None
    problems: str | None = None
    rating: int | None = None
    revision_lesson: str | None = None
    revision_rating: int | None = None
    attitude: int | None = None
    added_points: int = 0
    notes: str | None = None
    problem_ids: list[UUID] = field(default_factory=list)


class DailyRecordService:
    def __init__(
        self, records: DailyRecordRepository, policy: ScoringPolicy = DEFAULT_SCORING
    ) -> None:
        self._records = records
        self._policy = policy

    async def create(self, data: CreateDailyRecordInput) -> DailyRecord:
        record = DailyRecord.create(
            student_id=data.student_id,
            teacher_id=data.teacher_id,
            halaqah_id=data.halaqah_id,
            record_date=data.record_date or datetime.now(UTC).date(),
            present=data.present,
            excused=data.excused,
            late=data.late,
            excuse_reason=data.excuse_reason,
            exam_from=data.exam_from,
            exam_to=data.exam_to,
            exam_total=data.exam_total,
            homework=data.homework,
            problems=data.problems,
            rating=data.rating,
            revision_lesson=data.revision_lesson,
            revision_rating=data.revision_rating,
            attitude=data.attitude,
            added_points=data.added_points,
            notes=data.notes,
            problem_ids=data.problem_ids,
        )
        record.apply_scoring(self._policy)
        await self._records.add(record)
        return await self.get(record.id)

    async def set_attendance(
        self,
        *,
        halaqah_id: UUID,
        teacher_id: UUID,
        record_date: date,
        entries: list[BulkAttendanceEntry],
    ) -> tuple[int, int]:
        """Mark a whole halaqah present/absent for a date. Returns (created, updated).

        Existing records keep their assessment; only attendance (and the derived
        card scores) are refreshed.
        """
        existing = await self._records.list(
            Page(limit=500), halaqah_id=halaqah_id, record_date=record_date
        )
        by_student = {r.student_id: r for r in existing}
        created = updated = 0
        for entry in entries:
            record = by_student.get(entry.student_id)
            if record is not None:
                record.present = entry.present
                record.excused = entry.excused
                record.late = entry.late
                record.excuse_reason = entry.excuse_reason
                record.revalidate()
                record.apply_scoring(self._policy)
                await self._records.update(record)
                updated += 1
            else:
                record = DailyRecord.create(
                    student_id=entry.student_id,
                    teacher_id=teacher_id,
                    halaqah_id=halaqah_id,
                    record_date=record_date,
                    present=entry.present,
                    excused=entry.excused,
                    late=entry.late,
                    excuse_reason=entry.excuse_reason,
                )
                record.apply_scoring(self._policy)
                await self._records.add(record)
                created += 1
        return created, updated

    async def bulk_upsert(
        self,
        *,
        halaqah_id: UUID,
        teacher_id: UUID,
        entries: list[UpsertDailyRecordEntry],
    ) -> tuple[list[DailyRecord], int, int]:
        """Create-or-overwrite many records in one transaction.

        Returns ``(records, created, updated)``. Idempotent: replaying the same
        payload converges on the same state, which is what lets the offline client
        retry a failed upload without duplicating anything.
        """
        keys = [(e.student_id, e.record_date) for e in entries]
        existing = await self._records.find_by_natural_keys(keys)

        saved: list[DailyRecord] = []
        created = updated = 0
        for entry in entries:
            record = existing.get((entry.student_id, entry.record_date))
            if record is None:
                record = DailyRecord.create(
                    student_id=entry.student_id,
                    teacher_id=teacher_id,
                    halaqah_id=halaqah_id,
                    record_date=entry.record_date,
                    present=entry.present,
                    excused=entry.excused,
                    late=entry.late,
                    excuse_reason=entry.excuse_reason,
                    exam_from=entry.exam_from,
                    exam_to=entry.exam_to,
                    exam_total=entry.exam_total,
                    homework=entry.homework,
                    problems=entry.problems,
                    rating=entry.rating,
                    revision_lesson=entry.revision_lesson,
                    revision_rating=entry.revision_rating,
                    attitude=entry.attitude,
                    added_points=entry.added_points,
                    notes=entry.notes,
                    problem_ids=entry.problem_ids,
                )
                record.apply_scoring(self._policy)
                await self._records.add(record)
                created += 1
            else:
                record.teacher_id = teacher_id
                record.halaqah_id = halaqah_id
                record.present = entry.present
                record.excused = entry.excused
                record.late = entry.late
                record.excuse_reason = entry.excuse_reason
                record.exam_from = entry.exam_from
                record.exam_to = entry.exam_to
                record.exam_total = _as_decimal(entry.exam_total)
                record.homework = entry.homework
                record.problems = entry.problems
                record.rating = entry.rating
                record.revision_lesson = entry.revision_lesson
                record.revision_rating = entry.revision_rating
                record.attitude = entry.attitude
                record.added_points = entry.added_points
                record.notes = entry.notes
                record.problem_ids = list(entry.problem_ids)
                record.revalidate()
                record.apply_scoring(self._policy)
                await self._records.update(record)
                updated += 1
            saved.append(await self.get(record.id))
        return saved, created, updated

    async def latest_recitations(
        self, student_ids: list[UUID], *, before: date | None = None
    ) -> tuple[dict[UUID, DailyRecord], dict[UUID, str]]:
        """Per student: the last record with a recitation, and the last homework set.

        Deliberately unbounded in time — the app used to look back a fixed three
        months, so a student who had been away longer showed no «آخر تسميع» at all.
        """
        return (
            await self._records.latest_recitations(student_ids, before=before),
            await self._records.latest_homework(student_ids, before=before),
        )

    async def get(self, record_id: UUID) -> DailyRecord:
        record = await self._records.get_by_id(record_id)
        if record is None:
            raise DailyRecordNotFoundError
        return record

    async def list(
        self,
        page: Page,
        *,
        student_id: UUID | None = None,
        teacher_id: UUID | None = None,
        halaqah_id: UUID | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
        record_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[DailyRecord], int]:
        records = await self._records.list(
            page,
            student_id=student_id,
            teacher_id=teacher_id,
            halaqah_id=halaqah_id,
            halaqah_ids=halaqah_ids,
            record_date=record_date,
            date_from=date_from,
            date_to=date_to,
        )
        total = await self._records.count(
            student_id=student_id,
            teacher_id=teacher_id,
            halaqah_id=halaqah_id,
            halaqah_ids=halaqah_ids,
            record_date=record_date,
            date_from=date_from,
            date_to=date_to,
        )
        return records, total

    async def update(self, record_id: UUID, data: UpdateDailyRecordInput) -> DailyRecord:
        record = await self.get(record_id)
        if data.teacher_id is not UNSET:
            record.teacher_id = data.teacher_id
        if data.halaqah_id is not UNSET:
            record.halaqah_id = data.halaqah_id
        if data.record_date is not UNSET:
            record.record_date = data.record_date
        if data.present is not UNSET:
            record.present = data.present
        if data.excused is not UNSET:
            record.excused = data.excused
        if data.late is not UNSET:
            record.late = data.late
        if data.excuse_reason is not UNSET:
            record.excuse_reason = data.excuse_reason
        if data.exam_from is not UNSET:
            record.exam_from = data.exam_from
        if data.exam_to is not UNSET:
            record.exam_to = data.exam_to
        if data.exam_total is not UNSET:
            record.exam_total = _as_decimal(data.exam_total)
        if data.homework is not UNSET:
            record.homework = data.homework
        if data.problems is not UNSET:
            record.problems = data.problems
        if data.rating is not UNSET:
            record.rating = data.rating
        if data.revision_lesson is not UNSET:
            record.revision_lesson = data.revision_lesson
        if data.revision_rating is not UNSET:
            record.revision_rating = data.revision_rating
        if data.attitude is not UNSET:
            record.attitude = data.attitude
        if data.added_points is not UNSET:
            record.added_points = data.added_points
        if data.notes is not UNSET:
            record.notes = data.notes
        if data.problem_ids is not UNSET:
            record.problem_ids = list(data.problem_ids)
        record.revalidate()
        record.apply_scoring(self._policy)
        await self._records.update(record)
        return await self.get(record_id)

    async def delete(self, record_id: UUID) -> None:
        record = await self.get(record_id)
        await self._records.delete(record)
