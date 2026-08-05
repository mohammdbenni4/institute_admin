"""Upcoming exams presentation layer: Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from institute_administration.modules.upcoming_exams.domain import ExamStatus, UpcomingExamView


class UpcomingExamResponse(BaseModel):
    id: UUID
    student_id: UUID
    student_name: str
    teacher_id: UUID
    teacher_name: str
    halaqah_id: UUID
    halaqah_name: str
    scheduled_date: date
    part: int | None
    exam_from: int | None
    exam_to: int | None
    notes: str | None
    status: ExamStatus
    status_label: str
    # Ready-made Arabic description of the coverage, e.g. «الجزء 5 · من 3 إلى 8».
    summary: str

    @classmethod
    def from_view(cls, view: UpcomingExamView) -> UpcomingExamResponse:
        return cls(
            id=view.id,
            student_id=view.student_id,
            student_name=view.student_name,
            teacher_id=view.teacher_id,
            teacher_name=view.teacher_name,
            halaqah_id=view.halaqah_id,
            halaqah_name=view.halaqah_name,
            scheduled_date=view.scheduled_date,
            part=view.part,
            exam_from=view.exam_from,
            exam_to=view.exam_to,
            notes=view.notes,
            status=view.status,
            status_label=view.status_label,
            summary=view.summary,
        )


class UpcomingExamListResponse(BaseModel):
    items: list[UpcomingExamResponse]
    total: int
    limit: int
    offset: int


class NextExamItem(BaseModel):
    """The soonest pending exam for one student (null when none is planned)."""

    student_id: UUID
    exam: UpcomingExamResponse | None = None


class NextExamsResponse(BaseModel):
    items: list[NextExamItem]


class UpcomingExamCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: UUID
    halaqah_id: UUID
    scheduled_date: date
    part: int | None = Field(default=None, ge=1, le=30)
    exam_from: int | None = Field(default=None, ge=0)
    exam_to: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=1000)
    teacher_id: UUID | None = None


class UpcomingExamUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheduled_date: date | None = None
    part: int | None = Field(default=None, ge=1, le=30)
    exam_from: int | None = Field(default=None, ge=0)
    exam_to: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=1000)
    status: ExamStatus | None = None
    # Names of optional fields to blank out, since `null` here means "unchanged".
    clear: list[str] = Field(default_factory=list)

    created_at: datetime | None = None  # accepted and ignored; keeps clients simple
