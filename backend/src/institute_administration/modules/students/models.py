"""Students infrastructure: the ``students`` ORM table."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from institute_administration.modules.students.domain import OrphanStatus


class StudentModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "students"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    father_name: Mapped[str] = mapped_column(String(255), nullable=False)
    father_number: Mapped[str] = mapped_column(String(40), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    mother_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    orphan_of: Mapped[OrphanStatus | None] = mapped_column(
        Enum(
            OrphanStatus,
            name="orphan_status",
            native_enum=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=True,
    )
    residential_area: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accepted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    halaqah_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("halaqahs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
