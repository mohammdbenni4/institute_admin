"""Halaqah-type infrastructure: the ``halaqah_types`` ORM table."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class HalaqahTypeModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "halaqah_types"

    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
