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


class AttendanceStudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: UUID
    student_name: str
    father_number: str | None
    halaqah_id: UUID | None
    halaqah_name: str | None
    teacher_id: UUID | None
    teacher_name: str | None
    present: int
    late: int
    absent: int
    excused: int
    total: int
    rate: int
    days: str
    """One character per day of the window: ``P`` present, ``L`` late, ``A`` absent,
    ``E`` excused, ``.`` no record."""


class AttendanceMatrixResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_from: date
    date_to: date
    days: int
    items: list[AttendanceStudentResponse]
    total: int
    limit: int
    offset: int
    students: int
    total_present: int
    total_late: int
    total_absent: int
    total_excused: int
    average_rate: int
