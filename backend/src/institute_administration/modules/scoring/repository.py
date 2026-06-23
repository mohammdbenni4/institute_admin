"""Scoring settings infrastructure: SQLAlchemy repository."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.modules.daily_records.domain import DEFAULT_SCORING, ScoringPolicy
from institute_administration.modules.scoring.models import ScoringSettingsModel


@dataclass(frozen=True)
class ScoringSettings:
    present_points: int
    rating_4_points: int
    rating_3_points: int
    rating_2_points: int
    rating_1_points: int
    revision_4_points: int
    revision_3_points: int
    revision_2_points: int
    revision_1_points: int
    attitude_3_points: int
    attitude_2_points: int
    attitude_1_points: int
    absent_points: int = 0
    excused_points: int = 0

    @classmethod
    def from_default(cls) -> ScoringSettings:
        return cls(
            present_points=DEFAULT_SCORING.present_points,
            rating_4_points=DEFAULT_SCORING.rating_points[4],
            rating_3_points=DEFAULT_SCORING.rating_points[3],
            rating_2_points=DEFAULT_SCORING.rating_points[2],
            rating_1_points=DEFAULT_SCORING.rating_points[1],
            revision_4_points=DEFAULT_SCORING.revision_points[4],
            revision_3_points=DEFAULT_SCORING.revision_points[3],
            revision_2_points=DEFAULT_SCORING.revision_points[2],
            revision_1_points=DEFAULT_SCORING.revision_points[1],
            attitude_3_points=DEFAULT_SCORING.attitude_points[3],
            attitude_2_points=DEFAULT_SCORING.attitude_points[2],
            attitude_1_points=DEFAULT_SCORING.attitude_points[1],
            absent_points=DEFAULT_SCORING.absent_points,
            excused_points=DEFAULT_SCORING.excused_points,
        )

    def to_policy(self) -> ScoringPolicy:
        return ScoringPolicy(
            present_points=self.present_points,
            absent_points=self.absent_points,
            excused_points=self.excused_points,
            rating_points={
                4: self.rating_4_points,
                3: self.rating_3_points,
                2: self.rating_2_points,
                1: self.rating_1_points,
            },
            revision_points={
                4: self.revision_4_points,
                3: self.revision_3_points,
                2: self.revision_2_points,
                1: self.revision_1_points,
            },
            attitude_points={
                3: self.attitude_3_points,
                2: self.attitude_2_points,
                1: self.attitude_1_points,
            },
        )


def _to_settings(m: ScoringSettingsModel) -> ScoringSettings:
    return ScoringSettings(
        present_points=m.present_points,
        rating_4_points=m.rating_4_points,
        rating_3_points=m.rating_3_points,
        rating_2_points=m.rating_2_points,
        rating_1_points=m.rating_1_points,
        revision_4_points=m.revision_4_points,
        revision_3_points=m.revision_3_points,
        revision_2_points=m.revision_2_points,
        revision_1_points=m.revision_1_points,
        attitude_3_points=m.attitude_3_points,
        attitude_2_points=m.attitude_2_points,
        attitude_1_points=m.attitude_1_points,
        absent_points=m.absent_points,
        excused_points=m.excused_points,
    )


class SqlAlchemyScoringSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _model(self) -> ScoringSettingsModel | None:
        result = await self._session.execute(select(ScoringSettingsModel).limit(1))
        return result.scalar_one_or_none()

    async def get(self) -> ScoringSettings:
        model = await self._model()
        return _to_settings(model) if model else ScoringSettings.from_default()

    async def get_policy(self) -> ScoringPolicy:
        model = await self._model()
        return _to_settings(model).to_policy() if model else DEFAULT_SCORING

    async def upsert(self, settings: ScoringSettings) -> ScoringSettings:
        model = await self._model()
        if model is None:
            model = ScoringSettingsModel()
            self._session.add(model)
        model.present_points = settings.present_points
        model.rating_4_points = settings.rating_4_points
        model.rating_3_points = settings.rating_3_points
        model.rating_2_points = settings.rating_2_points
        model.rating_1_points = settings.rating_1_points
        model.revision_4_points = settings.revision_4_points
        model.revision_3_points = settings.revision_3_points
        model.revision_2_points = settings.revision_2_points
        model.revision_1_points = settings.revision_1_points
        model.attitude_3_points = settings.attitude_3_points
        model.attitude_2_points = settings.attitude_2_points
        model.attitude_1_points = settings.attitude_1_points
        model.absent_points = settings.absent_points
        model.excused_points = settings.excused_points
        await self._session.flush()
        return _to_settings(model)
