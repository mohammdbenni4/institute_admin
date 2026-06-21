"""Daily records infrastructure: the ``daily_records`` ORM table.

The ``card_*`` and ``total_points`` columns are denormalised copies of values
the domain derives (see :mod:`~institute_administration.modules.daily_records.domain`);
the repository writes them from the entity so they stay authoritative there.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class DailyRecordModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_records"
    __table_args__ = (
        UniqueConstraint("student_id", "record_date"),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 4", name="rating_range"),
        CheckConstraint(
            "revision_rating IS NULL OR revision_rating BETWEEN 1 AND 4",
            name="revision_rating_range",
        ),
        CheckConstraint("attitude IS NULL OR attitude BETWEEN 1 AND 3", name="attitude_range"),
        CheckConstraint("exam_from IS NULL OR exam_from >= 0", name="exam_from_non_negative"),
        CheckConstraint("exam_to IS NULL OR exam_to >= 0", name="exam_to_non_negative"),
        CheckConstraint("exam_total IS NULL OR exam_total >= 0", name="exam_total_non_negative"),
        CheckConstraint("added_points >= 0", name="added_points_non_negative"),
    )

    student_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("teachers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    halaqah_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("halaqahs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    present: Mapped[bool] = mapped_column(Boolean, nullable=False)

    exam_from: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    exam_to: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    exam_total: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    homework: Mapped[str | None] = mapped_column(Text, nullable=True)
    problems: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    revision_lesson: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision_rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    attitude: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    added_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Denormalised, domain-derived reward-card scores.
    card_present: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    card_exam: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    card_attitude: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    total_points: Mapped[int] = mapped_column(SmallInteger, nullable=False)
