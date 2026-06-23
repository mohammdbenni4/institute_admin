"""Problems infrastructure: ORM tables for problem_levels and problems."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ProblemLevelModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named category for grouping problems (e.g. نطق, حفظ, سلوك)."""

    __tablename__ = "problem_levels"

    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)


class ProblemModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A specific difficulty that can be tagged on a student's daily record."""

    __tablename__ = "problems"
    __table_args__ = (UniqueConstraint("name", "problem_level_id", name="uq_problems_name_level"),)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    problem_level_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("problem_levels.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
