"""Scoring infrastructure: SQLAlchemy repositories for the institute-wide
settings row, the named presets, and the per-student policy resolver."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.modules.daily_records.domain import DEFAULT_SCORING, ScoringPolicy
from institute_administration.modules.scoring.models import ScoringPresetModel, ScoringSettingsModel
from institute_administration.modules.students.models import StudentModel
from institute_administration.shared.domain import ConflictError, EntityNotFoundError


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
    late_points: int = 5

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
            late_points=DEFAULT_SCORING.late_points,
        )

    def to_policy(self) -> ScoringPolicy:
        return ScoringPolicy(
            present_points=self.present_points,
            absent_points=self.absent_points,
            excused_points=self.excused_points,
            late_points=self.late_points,
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


def _apply_settings(model: ScoringSettingsModel | ScoringPresetModel, s: ScoringSettings) -> None:
    """Copy the fifteen weights onto either weights-carrying table."""
    for name in (f.name for f in fields(ScoringSettings)):
        setattr(model, name, getattr(s, name))


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
        late_points=m.late_points,
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
        _apply_settings(model, settings)
        await self._session.flush()
        return _to_settings(model)


# --- Named presets ----------------------------------------------------------------


@dataclass(frozen=True)
class ScoringPreset:
    """A named set of weights, plus the identity a student is pinned to."""

    id: UUID
    name: str
    settings: ScoringSettings


_PRESET_FIELDS = tuple(f.name for f in fields(ScoringSettings))


def _preset_settings(m: ScoringPresetModel) -> ScoringSettings:
    return ScoringSettings(**{name: getattr(m, name) for name in _PRESET_FIELDS})


def _to_preset(m: ScoringPresetModel) -> ScoringPreset:
    return ScoringPreset(id=m.id, name=m.name, settings=_preset_settings(m))


class DuplicatePresetNameError(ConflictError):
    def __init__(self, message: str = "يوجد نظام تسعير آخر بنفس الاسم") -> None:
        super().__init__(message)


class ScoringPresetNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "نظام تسعير النقاط غير موجود") -> None:
        super().__init__(message)


class SqlAlchemyScoringPresetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[ScoringPreset]:
        result = await self._session.execute(
            select(ScoringPresetModel).order_by(ScoringPresetModel.name)
        )
        return [_to_preset(m) for m in result.scalars()]

    async def get(self, preset_id: UUID) -> ScoringPreset:
        model = await self._session.get(ScoringPresetModel, preset_id)
        if model is None:
            raise ScoringPresetNotFoundError
        return _to_preset(model)

    async def create(self, name: str, settings: ScoringSettings) -> ScoringPreset:
        model = ScoringPresetModel(name=name.strip())
        _apply_settings(model, settings)
        self._session.add(model)
        await self._flush()
        return _to_preset(model)

    async def update(
        self, preset_id: UUID, *, name: str, settings: ScoringSettings
    ) -> ScoringPreset:
        model = await self._session.get(ScoringPresetModel, preset_id)
        if model is None:
            raise ScoringPresetNotFoundError
        model.name = name.strip()
        _apply_settings(model, settings)
        await self._flush()
        return _to_preset(model)

    async def delete(self, preset_id: UUID) -> None:
        model = await self._session.get(ScoringPresetModel, preset_id)
        if model is None:
            raise ScoringPresetNotFoundError
        # students.scoring_preset_id is ON DELETE SET NULL, so the students it priced
        # simply fall back to the institute-wide settings.
        await self._session.delete(model)
        await self._session.flush()

    async def _flush(self) -> None:
        try:
            await self._session.flush()
        except IntegrityError as exc:  # the only constraint is the unique name
            raise DuplicatePresetNameError from exc


class StudentScoringPolicyResolver:
    """Answers "which weights price this student's card?".

    A student pinned to a preset (``students.scoring_preset_id``) is scored by it;
    everyone else by the institute-wide ``scoring_settings`` row. Both are loaded
    at most once per request and cached, so a hundred-record bulk upload costs two
    queries rather than two hundred.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._default: ScoringPolicy | None = None
        self._by_student: dict[UUID, ScoringPolicy] = {}

    async def _fallback(self) -> ScoringPolicy:
        if self._default is None:
            self._default = await SqlAlchemyScoringSettingsRepository(self._session).get_policy()
        return self._default

    async def prime(self, student_ids: Sequence[UUID]) -> None:
        """Load the presets for a batch of students in a single query."""
        unknown = [sid for sid in set(student_ids) if sid not in self._by_student]
        if not unknown:
            return
        result = await self._session.execute(
            select(StudentModel.id, ScoringPresetModel)
            .join(ScoringPresetModel, StudentModel.scoring_preset_id == ScoringPresetModel.id)
            .where(StudentModel.id.in_(unknown))
        )
        priced = {}
        for student_id, preset in result.all():
            priced[student_id] = _preset_settings(preset).to_policy()
        fallback = await self._fallback()
        # Cache the misses too: a student with no preset must not re-query on every record.
        for sid in unknown:
            self._by_student[sid] = priced.get(sid, fallback)

    async def for_student(self, student_id: UUID) -> ScoringPolicy:
        if student_id not in self._by_student:
            await self.prime([student_id])
        return self._by_student[student_id]
