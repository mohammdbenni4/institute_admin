"""Upcoming exams infrastructure: the ``upcoming_exams`` ORM table."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, SmallInteger, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class UpcomingExamModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One planned examination for one student."""

    __tablename__ = "upcoming_exams"
    __table_args__ = (
        CheckConstraint("part IS NULL OR part BETWEEN 1 AND 30", name="part_range"),
        CheckConstraint("exam_from IS NULL OR exam_from >= 0", name="exam_from_non_negative"),
        CheckConstraint("exam_to IS NULL OR exam_to >= 0", name="exam_to_non_negative"),
    )

    student_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    halaqah_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("halaqahs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # الجزء (1 to 30) and/or an explicit page range — the teacher fills what applies.
    part: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    exam_from: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    exam_to: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 'pending' | 'done' | 'cancelled' — see domain.ExamStatus.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
