"""Scoring settings infrastructure: the single-row ``scoring_settings`` table."""

from __future__ import annotations

from sqlalchemy import SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ScoringSettingsModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Institute-wide reward-card weights. Only one row is ever used."""

    __tablename__ = "scoring_settings"

    present_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5)
    rating_4_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=7)
    rating_3_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5)
    rating_2_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    rating_1_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    attitude_3_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    attitude_2_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    attitude_1_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
