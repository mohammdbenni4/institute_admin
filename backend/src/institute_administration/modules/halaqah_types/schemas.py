"""Halaqah-type presentation layer: Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from institute_administration.modules.halaqah_types.domain import HalaqahType


class HalaqahTypeResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, halaqah_type: HalaqahType) -> HalaqahTypeResponse:
        return cls(
            id=halaqah_type.id,
            name=halaqah_type.name,
            created_at=halaqah_type.created_at,
            updated_at=halaqah_type.updated_at,
        )


class HalaqahTypeListResponse(BaseModel):
    items: list[HalaqahTypeResponse]
    total: int
    limit: int
    offset: int


class HalaqahTypeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)


class HalaqahTypeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=150)
