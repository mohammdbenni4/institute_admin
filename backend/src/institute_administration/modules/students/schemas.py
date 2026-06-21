"""Students presentation layer: Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from institute_administration.modules.students.domain import OrphanStatus, Student


class StudentResponse(BaseModel):
    id: UUID
    full_name: str
    father_name: str
    father_number: str
    date_of_birth: date | None
    mother_number: str | None
    orphan_of: OrphanStatus | None
    residential_area: str | None
    accepted_at: date | None
    notes: str | None
    halaqah_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, student: Student) -> StudentResponse:
        return cls(
            id=student.id,
            full_name=student.full_name,
            father_name=student.father_name,
            father_number=student.father_number,
            date_of_birth=student.date_of_birth,
            mother_number=student.mother_number,
            orphan_of=student.orphan_of,
            residential_area=student.residential_area,
            accepted_at=student.accepted_at,
            notes=student.notes,
            halaqah_id=student.halaqah_id,
            created_at=student.created_at,
            updated_at=student.updated_at,
        )


class StudentListResponse(BaseModel):
    items: list[StudentResponse]
    total: int
    limit: int
    offset: int


class StudentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=255)
    father_name: str = Field(min_length=1, max_length=255)
    father_number: str = Field(min_length=1, max_length=40)
    date_of_birth: date | None = None
    mother_number: str | None = Field(default=None, max_length=40)
    orphan_of: OrphanStatus | None = None
    residential_area: str | None = Field(default=None, max_length=255)
    accepted_at: date | None = None
    notes: str | None = None
    halaqah_id: UUID | None = None


class StudentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    father_name: str | None = Field(default=None, min_length=1, max_length=255)
    father_number: str | None = Field(default=None, min_length=1, max_length=40)
    date_of_birth: date | None = None
    mother_number: str | None = Field(default=None, max_length=40)
    orphan_of: OrphanStatus | None = None
    residential_area: str | None = Field(default=None, max_length=255)
    accepted_at: date | None = None
    notes: str | None = None
    halaqah_id: UUID | None = None
