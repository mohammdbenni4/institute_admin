"""Teachers presentation layer: Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from institute_administration.modules.teachers.domain import TeacherView


class TeacherResponse(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str
    email: EmailStr
    date_of_birth: date | None
    is_active: bool
    academic_study: str
    islamic_study: str
    is_assistant: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_view(cls, view: TeacherView) -> TeacherResponse:
        return cls(
            id=view.id,
            user_id=view.user_id,
            full_name=view.full_name,
            email=view.email,
            date_of_birth=view.date_of_birth,
            is_active=view.is_active,
            academic_study=view.academic_study,
            islamic_study=view.islamic_study,
            is_assistant=view.is_assistant,
            created_at=view.created_at,
            updated_at=view.updated_at,
        )


class TeacherListResponse(BaseModel):
    items: list[TeacherResponse]
    total: int
    limit: int
    offset: int


class TeacherCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    # Length policy is a domain invariant (RawPassword) so the rejection reason
    # reaches the user in Arabic instead of a generic 422 validation error.
    password: str
    academic_study: str = Field(min_length=1, max_length=255)
    islamic_study: str = Field(min_length=1, max_length=255)
    is_assistant: bool = False
    date_of_birth: date | None = None


class TeacherUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    password: str | None = None  # length policy enforced by the domain (RawPassword)
    date_of_birth: date | None = None
    is_active: bool | None = None
    academic_study: str | None = Field(default=None, min_length=1, max_length=255)
    islamic_study: str | None = Field(default=None, min_length=1, max_length=255)
    is_assistant: bool | None = None
