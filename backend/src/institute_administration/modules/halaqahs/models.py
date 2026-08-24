"""Halaqahs infrastructure: the ``halaqahs`` table and its teacher membership."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class HalaqahModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "halaqahs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # The «المعلم المسؤول» — the one name printed on the student's paper report and
    # its signature line. Teaching membership lives in `halaqah_teachers`; this column
    # only says which of those members is the responsible one, and is always among them.
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


class HalaqahTeacherModel(Base):
    """Which teachers may teach a halaqah — the authority for access control.

    A halaqah has many teachers and a teacher has many halaqahs. Every member has
    the same rights over the halaqah's students and records; the halaqah's
    ``teacher_id`` singles out one of them as the responsible teacher for display
    purposes only, and is kept in this table too (see the repository's
    ``_sync_membership``), so no query has to special-case it.

    ``ON DELETE CASCADE`` on both sides is safe: removing a halaqah drops its
    memberships, and removing a teacher drops the halaqahs they merely assisted with.
    A teacher who is *responsible* for a halaqah cannot be deleted at all — that is
    still blocked by ``halaqahs.teacher_id``'s ``ON DELETE RESTRICT``.
    """

    __tablename__ = "halaqah_teachers"

    halaqah_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("halaqahs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    teacher_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("teachers.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
