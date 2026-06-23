"""Daily records infrastructure: SQLAlchemy repository implementation."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.modules.daily_records.domain import (
    DailyRecord,
    DailyRecordRepository,
    DuplicateDailyRecordError,
    InvalidHalaqahError,
    InvalidStudentError,
    InvalidTeacherError,
)
from institute_administration.modules.daily_records.models import (
    DailyRecordModel,
    DailyRecordProblemModel,
)
from institute_administration.shared.application.pagination import Page


def _to_entity(model: DailyRecordModel, problem_ids: list[UUID] | None = None) -> DailyRecord:
    return DailyRecord(
        id=model.id,
        student_id=model.student_id,
        teacher_id=model.teacher_id,
        halaqah_id=model.halaqah_id,
        record_date=model.record_date,
        present=model.present,
        excused=model.excused,
        exam_from=model.exam_from,
        exam_to=model.exam_to,
        exam_total=model.exam_total,
        homework=model.homework,
        problems=model.problems,
        rating=model.rating,
        revision_lesson=model.revision_lesson,
        revision_rating=model.revision_rating,
        attitude=model.attitude,
        added_points=model.added_points,
        notes=model.notes,
        problem_ids=problem_ids or [],
        card_present=model.card_present,
        card_exam=model.card_exam,
        card_revision=model.card_revision,
        card_attitude=model.card_attitude,
        total_points=model.total_points,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply(model: DailyRecordModel, record: DailyRecord) -> None:
    model.student_id = record.student_id
    model.teacher_id = record.teacher_id
    model.halaqah_id = record.halaqah_id
    model.record_date = record.record_date
    model.present = record.present
    model.excused = record.excused
    model.exam_from = record.exam_from
    model.exam_to = record.exam_to
    model.exam_total = record.exam_total
    model.homework = record.homework
    model.problems = record.problems
    model.rating = record.rating
    model.revision_lesson = record.revision_lesson
    model.revision_rating = record.revision_rating
    model.attitude = record.attitude
    model.added_points = record.added_points
    model.notes = record.notes
    # Persist the domain-derived reward-card scores.
    model.card_present = record.card_present
    model.card_exam = record.card_exam
    model.card_revision = record.card_revision
    model.card_attitude = record.card_attitude
    model.total_points = record.total_points


class SqlAlchemyDailyRecordRepository(DailyRecordRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- junction table helpers -----------------------------------------------

    async def _sync_problems(self, record_id: UUID, problem_ids: list[UUID]) -> None:
        await self._session.execute(
            delete(DailyRecordProblemModel).where(
                DailyRecordProblemModel.daily_record_id == record_id
            )
        )
        for pid in problem_ids:
            self._session.add(
                DailyRecordProblemModel(daily_record_id=record_id, problem_id=pid)
            )

    async def _load_problem_ids_by_records(
        self, record_ids: list[UUID]
    ) -> dict[UUID, list[UUID]]:
        if not record_ids:
            return {}
        result = await self._session.execute(
            select(DailyRecordProblemModel).where(
                DailyRecordProblemModel.daily_record_id.in_(record_ids)
            )
        )
        by_record: dict[UUID, list[UUID]] = {rid: [] for rid in record_ids}
        for row in result.scalars().all():
            by_record[row.daily_record_id].append(row.problem_id)
        return by_record

    # -- CRUD -----------------------------------------------------------------

    async def add(self, record: DailyRecord) -> None:
        model = DailyRecordModel(id=record.id)
        _apply(model, record)
        self._session.add(model)
        await self._session.flush()
        await self._sync_problems(record.id, record.problem_ids)
        await self._flush()

    async def update(self, record: DailyRecord) -> None:
        model = await self._session.get(DailyRecordModel, record.id)
        if model is None:  # pragma: no cover - guarded by the service layer
            return
        _apply(model, record)
        await self._session.flush()
        await self._sync_problems(record.id, record.problem_ids)
        await self._flush()

    async def get_by_id(self, record_id: UUID) -> DailyRecord | None:
        model = await self._session.get(DailyRecordModel, record_id)
        if model is None:
            return None
        by_record = await self._load_problem_ids_by_records([record_id])
        return _to_entity(model, by_record.get(record_id, []))

    async def list(
        self,
        page: Page,
        *,
        student_id: UUID | None = None,
        teacher_id: UUID | None = None,
        halaqah_id: UUID | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
        record_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[DailyRecord]:
        stmt = select(DailyRecordModel)
        if student_id is not None:
            stmt = stmt.where(DailyRecordModel.student_id == student_id)
        if teacher_id is not None:
            stmt = stmt.where(DailyRecordModel.teacher_id == teacher_id)
        if halaqah_id is not None:
            stmt = stmt.where(DailyRecordModel.halaqah_id == halaqah_id)
        if halaqah_ids is not None:
            stmt = stmt.where(DailyRecordModel.halaqah_id.in_(halaqah_ids))
        if record_date is not None:
            stmt = stmt.where(DailyRecordModel.record_date == record_date)
        if date_from is not None:
            stmt = stmt.where(DailyRecordModel.record_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(DailyRecordModel.record_date <= date_to)
        stmt = (
            stmt.order_by(DailyRecordModel.record_date.desc(), DailyRecordModel.created_at.desc())
            .limit(page.limit)
            .offset(page.offset)
        )
        result = await self._session.execute(stmt)
        models = list(result.scalars().all())
        if not models:
            return []
        record_ids = [m.id for m in models]
        by_record = await self._load_problem_ids_by_records(record_ids)
        return [_to_entity(m, by_record.get(m.id, [])) for m in models]

    async def count(
        self,
        *,
        student_id: UUID | None = None,
        teacher_id: UUID | None = None,
        halaqah_id: UUID | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
        record_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(DailyRecordModel)
        if student_id is not None:
            stmt = stmt.where(DailyRecordModel.student_id == student_id)
        if teacher_id is not None:
            stmt = stmt.where(DailyRecordModel.teacher_id == teacher_id)
        if halaqah_id is not None:
            stmt = stmt.where(DailyRecordModel.halaqah_id == halaqah_id)
        if halaqah_ids is not None:
            stmt = stmt.where(DailyRecordModel.halaqah_id.in_(halaqah_ids))
        if record_date is not None:
            stmt = stmt.where(DailyRecordModel.record_date == record_date)
        if date_from is not None:
            stmt = stmt.where(DailyRecordModel.record_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(DailyRecordModel.record_date <= date_to)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def delete(self, record: DailyRecord) -> None:
        model = await self._session.get(DailyRecordModel, record.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def _flush(self) -> None:
        try:
            await self._session.flush()
        except IntegrityError as exc:
            detail = str(exc.orig)
            if "uq_daily_records_student_id" in detail:
                raise DuplicateDailyRecordError from exc
            if "fk_daily_records_student_id" in detail:
                raise InvalidStudentError from exc
            if "fk_daily_records_teacher_id" in detail:
                raise InvalidTeacherError from exc
            if "fk_daily_records_halaqah_id" in detail:
                raise InvalidHalaqahError from exc
            raise
