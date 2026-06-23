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
    exam_from: int | None
    exam_to: int | None
    exam_total: int | None
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
            exam_from=record.exam_from,
            exam_to=record.exam_to,
            exam_total=record.exam_total,
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
    record_date: date | None = None
    exam_from: int | None = Field(default=None, ge=0)
    exam_to: int | None = Field(default=None, ge=0)
    exam_total: int | None = Field(default=None, ge=0)
    homework: str | None = None
    problems: str | None = None
    rating: int | None = Field(default=None, ge=1, le=4)
    revision_lesson: str | None = None
    revision_rating: int | None = Field(default=None, ge=1, le=4)
    attitude: int | None = Field(default=None, ge=1, le=3)
    added_points: int = Field(default=0, ge=0)
    notes: str | None = None
    problem_ids: list[UUID] = Field(default_factory=list)


class BulkAttendanceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: UUID
    present: bool
    excused: bool = False


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


class DailyRecordUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    teacher_id: UUID | None = None
    halaqah_id: UUID | None = None
    record_date: date | None = None
    present: bool | None = None
    excused: bool | None = None
    exam_from: int | None = Field(default=None, ge=0)
    exam_to: int | None = Field(default=None, ge=0)
    exam_total: int | None = Field(default=None, ge=0)
    homework: str | None = None
    problems: str | None = None
    rating: int | None = Field(default=None, ge=1, le=4)
    revision_lesson: str | None = None
    revision_rating: int | None = Field(default=None, ge=1, le=4)
    attitude: int | None = Field(default=None, ge=1, le=3)
    added_points: int | None = Field(default=None, ge=0)
    notes: str | None = None
    problem_ids: list[UUID] = Field(default_factory=list)
