"""Times infrastructure: the ``times`` ORM table (one JSONB column per day)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

# Each day stores ``{"from": "HH:MM", "to": "HH:MM"}`` or NULL.
type DayColumn = dict[str, str] | None


class TimeModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "times"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    saturday: Mapped[DayColumn] = mapped_column(JSONB, nullable=True)
    sunday: Mapped[DayColumn] = mapped_column(JSONB, nullable=True)
    monday: Mapped[DayColumn] = mapped_column(JSONB, nullable=True)
    tuesday: Mapped[DayColumn] = mapped_column(JSONB, nullable=True)
    wednesday: Mapped[DayColumn] = mapped_column(JSONB, nullable=True)
    thursday: Mapped[DayColumn] = mapped_column(JSONB, nullable=True)
    friday: Mapped[DayColumn] = mapped_column(JSONB, nullable=True)

    def day_values(self) -> dict[str, Any]:
        return {
            "saturday": self.saturday,
            "sunday": self.sunday,
            "monday": self.monday,
            "tuesday": self.tuesday,
            "wednesday": self.wednesday,
            "thursday": self.thursday,
            "friday": self.friday,
        }
