"""Daily records infrastructure: SQLAlchemy repository implementation."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
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
from institute_administration.modules.daily_records.models import DailyRecordModel
from institute_administration.shared.application.pagination import Page


def _to_entity(model: DailyRecordModel) -> DailyRecord:
    return DailyRecord(
        id=model.id,
        student_id=model.student_id,
        teacher_id=model.teacher_id,
        halaqah_id=model.halaqah_id,
        record_date=model.record_date,
        present=model.present,
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
        card_present=model.card_present,
        card_exam=model.card_exam,
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
    model.card_attitude = record.card_attitude
    model.total_points = record.total_points


class SqlAlchemyDailyRecordRepository(DailyRecordRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: DailyRecord) -> None:
        model = DailyRecordModel(id=record.id)
        _apply(model, record)
        self._session.add(model)
        await self._flush()

    async def update(self, record: DailyRecord) -> None:
        model = await self._session.get(DailyRecordModel, record.id)
        if model is None:  # pragma: no cover - guarded by the service layer
            return
        _apply(model, record)
        await self._flush()

    async def get_by_id(self, record_id: UUID) -> DailyRecord | None:
        model = await self._session.get(DailyRecordModel, record_id)
        return _to_entity(model) if model else None

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
        return [_to_entity(m) for m in result.scalars().all()]

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
