"""Teachers infrastructure: the ``teachers`` ORM table."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class TeacherModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teachers"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    academic_study: Mapped[str] = mapped_column(String(255), nullable=False)
    islamic_study: Mapped[str] = mapped_column(String(255), nullable=False)
    is_assistant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
