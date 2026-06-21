"""Analytics presentation layer: Pydantic response schemas.

Built directly from the service dataclasses via ``from_attributes``.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    records: int
    present: int
    absent: int
    attendance_rate: float
    total_points: int
    active_students: int
    halaqahs: int


class LeaderboardEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    student_id: UUID
    student_name: str
    total_points: int
    sessions: int
    present_count: int


class HalaqahLeaderboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    halaqah_id: UUID
    halaqah_name: str
    students: list[LeaderboardEntryResponse]


class LeaderboardResponse(BaseModel):
    date_from: date
    date_to: date
    items: list[HalaqahLeaderboardResponse]


class AtRiskStudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: UUID
    student_name: str
    halaqah_id: UUID
    halaqah_name: str
    sessions: int
    absences: int
    total_points: int
    reasons: list[str]


class AtRiskResponse(BaseModel):
    date_from: date
    date_to: date
    items: list[AtRiskStudentResponse]
