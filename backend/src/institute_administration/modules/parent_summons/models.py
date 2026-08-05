"""Parent summons infrastructure: the ``parent_summons`` ORM table."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ParentSummonModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One request from a teacher to call a student's guardian in."""

    __tablename__ = "parent_summons"

    student_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    halaqah_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("halaqahs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # 'new' | 'reviewing' | 'completed' — see domain.SummonStatus.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new", index=True)
    # What the administration tells the teacher once the matter is handled.
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
