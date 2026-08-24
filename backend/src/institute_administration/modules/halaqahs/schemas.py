"""Halaqahs presentation layer: Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from institute_administration.modules.halaqahs.domain import HalaqahView


class TeacherBriefResponse(BaseModel):
    id: UUID
    name: str


class HalaqahResponse(BaseModel):
    id: UUID
    name: str
    level: str | None
    age: str | None
    # المعلم المسؤول — the single name the printed student report carries.
    teacher_id: UUID
    teacher_name: str
    # Everyone who may teach this halaqah, responsible teacher first.
    teachers: list[TeacherBriefResponse] = []
    halaqah_type_id: UUID
    halaqah_type_name: str
    time_id: UUID | None
    time_name: str | None = None
    schedule: dict[str, dict[str, str]] = {}
    number_of_students: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_view(cls, view: HalaqahView) -> HalaqahResponse:
        return cls(
            id=view.id,
            name=view.name,
            level=view.level,
            age=view.age,
            teacher_id=view.teacher_id,
            teacher_name=view.teacher_name,
            teachers=[TeacherBriefResponse(id=t.id, name=t.name) for t in view.teachers],
            halaqah_type_id=view.halaqah_type_id,
            halaqah_type_name=view.halaqah_type_name,
            time_id=view.time_id,
            time_name=view.time_name,
            schedule=view.schedule,
            number_of_students=view.number_of_students,
            created_at=view.created_at,
            updated_at=view.updated_at,
        )


class HalaqahListResponse(BaseModel):
    items: list[HalaqahResponse]
    total: int
    limit: int
    offset: int


class HalaqahCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    teacher_id: UUID
    # Additional teachers who may also teach this halaqah. The responsible
    # `teacher_id` is always a member and need not be repeated here.
    teacher_ids: list[UUID] | None = None
    halaqah_type_id: UUID
    level: str | None = Field(default=None, max_length=100)
    age: str | None = Field(default=None, max_length=100)
    time_id: UUID | None = None


class HalaqahUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    teacher_id: UUID | None = None
    # Omit to leave membership untouched; send a list to replace it wholesale.
    teacher_ids: list[UUID] | None = None
    halaqah_type_id: UUID | None = None
    level: str | None = Field(default=None, max_length=100)
    age: str | None = Field(default=None, max_length=100)
    time_id: UUID | None = None
