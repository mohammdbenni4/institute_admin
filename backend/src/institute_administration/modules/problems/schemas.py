"""Problems presentation layer: Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from institute_administration.modules.problems.domain import Problem, ProblemLevel


class ProblemLevelResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, level: ProblemLevel) -> ProblemLevelResponse:
        return cls(
            id=level.id,
            name=level.name,
            created_at=level.created_at,
            updated_at=level.updated_at,
        )


class ProblemLevelListResponse(BaseModel):
    items: list[ProblemLevelResponse]
    total: int
    limit: int
    offset: int


class ProblemLevelCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)


class ProblemLevelUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=150)


# ---------------------------------------------------------------------------
# Problem schemas
# ---------------------------------------------------------------------------


class ProblemResponse(BaseModel):
    id: UUID
    name: str
    level_id: UUID
    level_name: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, problem: Problem) -> ProblemResponse:
        return cls(
            id=problem.id,
            name=problem.name,
            level_id=problem.problem_level_id,
            level_name=problem.level_name,
            created_at=problem.created_at,
            updated_at=problem.updated_at,
        )


class ProblemListResponse(BaseModel):
    items: list[ProblemResponse]
    total: int
    limit: int
    offset: int


class ProblemCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    level_id: UUID


class ProblemUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    level_id: UUID | None = None
