"""Scoring infrastructure: the single-row ``scoring_settings`` table and the
named ``scoring_presets`` a student can be pinned to instead."""

from __future__ import annotations

from sqlalchemy import SmallInteger, String, UniqueConstraint
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
    revision_4_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=7, server_default="7"
    )
    revision_3_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=5, server_default="5"
    )
    revision_2_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=3, server_default="3"
    )
    revision_1_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    attitude_3_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    attitude_2_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    attitude_1_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    absent_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    excused_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    # «متأخر» — defaults to the present weight so lateness costs nothing until the
    # institute decides otherwise.
    late_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=5, server_default="5"
    )


class ScoringPresetModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named alternative to the institute-wide weights, assignable per student.

    Same fifteen columns as ``scoring_settings`` on purpose: a preset *is* a
    complete set of weights, not a patch over the defaults. Copying beats
    inheriting here — a teacher reading «نظام الرشيدي» sees every number that
    applies, and changing the institute default can never silently reprice a
    student who was deliberately put on a preset.
    """

    __tablename__ = "scoring_presets"
    __table_args__ = (UniqueConstraint("name", name="uq_scoring_presets_name"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    present_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=5, server_default="5"
    )
    rating_4_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=7, server_default="7"
    )
    rating_3_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=5, server_default="5"
    )
    rating_2_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=3, server_default="3"
    )
    rating_1_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    revision_4_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=7, server_default="7"
    )
    revision_3_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=5, server_default="5"
    )
    revision_2_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=3, server_default="3"
    )
    revision_1_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    attitude_3_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=3, server_default="3"
    )
    attitude_2_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=2, server_default="2"
    )
    attitude_1_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default="1"
    )
    absent_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    excused_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    late_points: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=5, server_default="5"
    )
