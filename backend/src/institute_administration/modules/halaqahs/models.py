"""Halaqahs infrastructure: the ``halaqahs`` ORM table."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class HalaqahModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "halaqahs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    teacher_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("teachers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    halaqah_type_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("halaqah_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    age: Mapped[str | None] = mapped_column(String(100), nullable=True)
    time_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("times.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
