"""Daily records presentation layer: Pydantic schemas.

Requests never carry the reward-card scores (``card_*``/``total_points``): those
are computed server-side from attendance, rating and attitude and only appear on
responses.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from institute_administration.modules.daily_records.domain import DailyRecord


class ProblemBrief(BaseModel):
    """Compact problem summary embedded in daily-record responses."""

    id: UUID
    name: str
    level_id: UUID
    level_name: str


class DailyRecordResponse(BaseModel):
    id: UUID
    student_id: UUID
    teacher_id: UUID
    halaqah_id: UUID
    record_date: date
    present: bool
    excused: bool
    late: bool
    excuse_reason: str | None
    exam_from: int | None
    exam_to: int | None
    exam_total: float | None
    homework: str | None
    problems: str | None
    rating: int | None
    revision_lesson: str | None
    revision_rating: int | None
    attitude: int | None
    added_points: int
    notes: str | None
    tagged_problems: list[ProblemBrief]
    card_present: int
    card_exam: int
    card_revision: int
    card_attitude: int
    total_points: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(
        cls, record: DailyRecord, resolved_problems: Sequence[Any] = ()
    ) -> DailyRecordResponse:
        return cls(
            id=record.id,
            student_id=record.student_id,
            teacher_id=record.teacher_id,
            halaqah_id=record.halaqah_id,
            record_date=record.record_date,
            present=record.present,
            excused=record.excused,
            late=record.late,
            excuse_reason=record.excuse_reason,
            exam_from=record.exam_from,
            exam_to=record.exam_to,
            exam_total=float(record.exam_total) if record.exam_total is not None else None,
            homework=record.homework,
            problems=record.problems,
            rating=record.rating,
            revision_lesson=record.revision_lesson,
            revision_rating=record.revision_rating,
            attitude=record.attitude,
            added_points=record.added_points,
            notes=record.notes,
            tagged_problems=[
                ProblemBrief(
                    id=p.id,
                    name=p.name,
                    level_id=p.problem_level_id,
                    level_name=p.level_name or "",
                )
                for p in resolved_problems
            ],
            card_present=record.card_present,
            card_exam=record.card_exam,
            card_revision=record.card_revision,
            card_attitude=record.card_attitude,
            total_points=record.total_points,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class DailyRecordListResponse(BaseModel):
    items: list[DailyRecordResponse]
    total: int
    limit: int
    offset: int


class DailyRecordCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: UUID
    teacher_id: UUID
    halaqah_id: UUID
    present: bool
    excused: bool = False
    late: bool = False
    excuse_reason: str | None = Field(default=None, max_length=500)
    record_date: date | None = None
    exam_from: int | None = Field(default=None, ge=0)
    exam_to: int | None = Field(default=None, ge=0)
    # Decimal on purpose: «نصف صفحة» is a real entry. Two places is plenty.
    exam_total: float | None = Field(default=None, ge=0, le=999.99, multiple_of=0.01)
    homework: str | None = None
    problems: str | None = None
    rating: int | None = Field(default=None, ge=1, le=4)
    revision_lesson: str | None = None
    revision_rating: int | None = Field(default=None, ge=1, le=4)
    attitude: int | None = Field(default=None, ge=1, le=3)
    # Signed: the teacher awards *and* deducts points («إضافة النقاط وحذفها»).
    added_points: int = Field(default=0, ge=-1000, le=1000)
    notes: str | None = None
    problem_ids: list[UUID] = Field(default_factory=list)


class BulkAttendanceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: UUID
    present: bool
    excused: bool = False
    late: bool = False
    excuse_reason: str | None = Field(default=None, max_length=500)


class BulkAttendanceRequest(BaseModel):
    """Mark attendance for many students of one halaqah on one date."""

    model_config = ConfigDict(extra="forbid")

    halaqah_id: UUID
    teacher_id: UUID
    record_date: date | None = None
    entries: list[BulkAttendanceItem] = Field(min_length=1)


class BulkAttendanceResponse(BaseModel):
    record_date: date
    created: int
    updated: int


class BulkUpsertItem(BaseModel):
    """One record keyed by ``(student_id, record_date)`` — a full overwrite."""

    model_config = ConfigDict(extra="forbid")

    student_id: UUID
    record_date: date
    present: bool = True
    excused: bool = False
    late: bool = False
    excuse_reason: str | None = Field(default=None, max_length=500)
    exam_from: int | None = Field(default=None, ge=0)
    exam_to: int | None = Field(default=None, ge=0)
    # Decimal on purpose: «نصف صفحة» is a real entry. Two places is plenty.
    exam_total: float | None = Field(default=None, ge=0, le=999.99, multiple_of=0.01)
    homework: str | None = None
    problems: str | None = None
    rating: int | None = Field(default=None, ge=1, le=4)
    revision_lesson: str | None = None
    revision_rating: int | None = Field(default=None, ge=1, le=4)
    attitude: int | None = Field(default=None, ge=1, le=3)
    # Signed: the teacher awards *and* deducts points («إضافة النقاط وحذفها»).
    added_points: int = Field(default=0, ge=-1000, le=1000)
    notes: str | None = None
    problem_ids: list[UUID] = Field(default_factory=list)


class BulkUpsertRequest(BaseModel):
    """Create-or-overwrite a batch of records in a single round trip.

    The offline teacher app drains its whole outbox with one call instead of a
    lookup plus a write per record, which is what made uploads slow on a weak
    connection.
    """

    model_config = ConfigDict(extra="forbid")

    halaqah_id: UUID
    teacher_id: UUID
    records: list[BulkUpsertItem] = Field(min_length=1, max_length=200)


class BulkUpsertResponse(BaseModel):
    items: list[DailyRecordResponse]
    created: int
    updated: int


class LatestRecitationItem(BaseModel):
    """A student's last recitation and the homework they were last assigned."""

    student_id: UUID
    last_recitation: DailyRecordResponse | None = None
    homework: str | None = None


class LatestRecitationsResponse(BaseModel):
    items: list[LatestRecitationItem]


class DailyRecordUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    teacher_id: UUID | None = None
    halaqah_id: UUID | None = None
    record_date: date | None = None
    present: bool | None = None
    excused: bool | None = None
    late: bool | None = None
    excuse_reason: str | None = Field(default=None, max_length=500)
    exam_from: int | None = Field(default=None, ge=0)
    exam_to: int | None = Field(default=None, ge=0)
    # Decimal on purpose: «نصف صفحة» is a real entry. Two places is plenty.
    exam_total: float | None = Field(default=None, ge=0, le=999.99, multiple_of=0.01)
    homework: str | None = None
    problems: str | None = None
    rating: int | None = Field(default=None, ge=1, le=4)
    revision_lesson: str | None = None
    revision_rating: int | None = Field(default=None, ge=1, le=4)
    attitude: int | None = Field(default=None, ge=1, le=3)
    added_points: int | None = Field(default=None, ge=-1000, le=1000)
    notes: str | None = None
    problem_ids: list[UUID] = Field(default_factory=list)
