"""Parent summons presentation layer: Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from institute_administration.modules.parent_summons.domain import (
    ParentSummonView,
    SummonStatus,
)


class ParentSummonResponse(BaseModel):
    id: UUID
    student_id: UUID
    student_name: str
    father_name: str | None
    father_number: str | None
    teacher_id: UUID
    teacher_name: str
    halaqah_id: UUID
    halaqah_name: str
    reason: str
    status: SummonStatus
    status_label: str
    admin_response: str | None
    handled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_view(cls, view: ParentSummonView) -> ParentSummonResponse:
        return cls(
            id=view.id,
            student_id=view.student_id,
            student_name=view.student_name,
            father_name=view.father_name,
            father_number=view.father_number,
            teacher_id=view.teacher_id,
            teacher_name=view.teacher_name,
            halaqah_id=view.halaqah_id,
            halaqah_name=view.halaqah_name,
            reason=view.reason,
            status=view.status,
            status_label=view.status_label,
            admin_response=view.admin_response,
            handled_at=view.handled_at,
            created_at=view.created_at,
            updated_at=view.updated_at,
        )


class ParentSummonListResponse(BaseModel):
    items: list[ParentSummonResponse]
    total: int
    limit: int
    offset: int
    # Queue sizes per status, for the admin badge and the teacher's panel header.
    counts: dict[SummonStatus, int]


class ParentSummonCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: UUID
    halaqah_id: UUID
    reason: str = Field(min_length=1, max_length=2000)
    # Teachers may create with their own id only; admins may name any teacher.
    teacher_id: UUID | None = None


class ParentSummonUpdateRequest(BaseModel):
    """Administration-only: move the request along and reply to the teacher."""

    model_config = ConfigDict(extra="forbid")

    status: SummonStatus | None = None
    admin_response: str | None = Field(default=None, max_length=2000)
