"""Upcoming exams infrastructure: SQLAlchemy repository."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.modules.halaqahs.models import HalaqahModel
from institute_administration.modules.identity.models import UserModel
from institute_administration.modules.students.models import StudentModel
from institute_administration.modules.teachers.models import TeacherModel
from institute_administration.modules.upcoming_exams.domain import ExamStatus, UpcomingExamView
from institute_administration.modules.upcoming_exams.models import UpcomingExamModel
from institute_administration.shared.application.pagination import Page


def _view(row: tuple) -> UpcomingExamView:  # type: ignore[type-arg]
    model, student_name, teacher_name, halaqah_name = row
    return UpcomingExamView(
        id=model.id,
        student_id=model.student_id,
        student_name=student_name,
        teacher_id=model.teacher_id,
        teacher_name=teacher_name,
        halaqah_id=model.halaqah_id,
        halaqah_name=halaqah_name,
        scheduled_date=model.scheduled_date,
        part=model.part,
        exam_from=model.exam_from,
        exam_to=model.exam_to,
        notes=model.notes,
        status=ExamStatus(model.status),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyUpcomingExamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _view_select(self) -> Select[tuple]:  # type: ignore[type-arg]
        return (
            select(
                UpcomingExamModel,
                StudentModel.full_name,
                UserModel.full_name,
                HalaqahModel.name,
            )
            .join(StudentModel, UpcomingExamModel.student_id == StudentModel.id)
            .join(TeacherModel, UpcomingExamModel.teacher_id == TeacherModel.id)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .join(HalaqahModel, UpcomingExamModel.halaqah_id == HalaqahModel.id)
        )

    def _filtered(
        self,
        stmt: Select[tuple],  # type: ignore[type-arg]
        *,
        student_id: UUID | None,
        halaqah_id: UUID | None,
        status: ExamStatus | None,
        date_from: date | None,
        halaqah_ids: frozenset[UUID] | None,
    ) -> Select[tuple]:  # type: ignore[type-arg]
        if student_id is not None:
            stmt = stmt.where(UpcomingExamModel.student_id == student_id)
        if halaqah_id is not None:
            stmt = stmt.where(UpcomingExamModel.halaqah_id == halaqah_id)
        if status is not None:
            stmt = stmt.where(UpcomingExamModel.status == status.value)
        if date_from is not None:
            stmt = stmt.where(UpcomingExamModel.scheduled_date >= date_from)
        if halaqah_ids is not None:
            stmt = stmt.where(UpcomingExamModel.halaqah_id.in_(halaqah_ids))
        return stmt

    async def add(
        self,
        *,
        student_id: UUID,
        teacher_id: UUID,
        halaqah_id: UUID,
        scheduled_date: date,
        part: int | None,
        exam_from: int | None,
        exam_to: int | None,
        notes: str | None,
    ) -> UUID:
        model = UpcomingExamModel(
            id=uuid4(),
            student_id=student_id,
            teacher_id=teacher_id,
            halaqah_id=halaqah_id,
            scheduled_date=scheduled_date,
            part=part,
            exam_from=exam_from,
            exam_to=exam_to,
            notes=notes,
            status=ExamStatus.PENDING.value,
        )
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def get_view(self, exam_id: UUID) -> UpcomingExamView | None:
        result = await self._session.execute(
            self._view_select().where(UpcomingExamModel.id == exam_id)
        )
        row = result.first()
        return _view(tuple(row)) if row else None

    async def list_views(
        self,
        page: Page,
        *,
        student_id: UUID | None = None,
        halaqah_id: UUID | None = None,
        status: ExamStatus | None = None,
        date_from: date | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
    ) -> list[UpcomingExamView]:
        stmt = self._filtered(
            self._view_select(),
            student_id=student_id,
            halaqah_id=halaqah_id,
            status=status,
            date_from=date_from,
            halaqah_ids=halaqah_ids,
        )
        result = await self._session.execute(
            stmt.order_by(UpcomingExamModel.scheduled_date).limit(page.limit).offset(page.offset)
        )
        return [_view(tuple(row)) for row in result.all()]

    async def count(
        self,
        *,
        student_id: UUID | None = None,
        halaqah_id: UUID | None = None,
        status: ExamStatus | None = None,
        date_from: date | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
    ) -> int:
        stmt = self._filtered(
            select(func.count()).select_from(UpcomingExamModel),
            student_id=student_id,
            halaqah_id=halaqah_id,
            status=status,
            date_from=date_from,
            halaqah_ids=halaqah_ids,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def next_per_student(
        self, student_ids: list[UUID], *, on_or_after: date
    ) -> dict[UUID, UpcomingExamView]:
        """The soonest still-pending exam for each student.

        One row per student via ``DISTINCT ON`` so a card can show «الاختبار القادم»
        for a whole halaqah in a single query.
        """
        if not student_ids:
            return {}
        stmt = (
            self._view_select()
            .where(
                UpcomingExamModel.student_id.in_(student_ids),
                UpcomingExamModel.status == ExamStatus.PENDING.value,
                UpcomingExamModel.scheduled_date >= on_or_after,
            )
            .distinct(UpcomingExamModel.student_id)
            .order_by(UpcomingExamModel.student_id, UpcomingExamModel.scheduled_date)
        )
        result = await self._session.execute(stmt)
        views = [_view(tuple(row)) for row in result.all()]
        return {v.student_id: v for v in views}

    async def update(
        self,
        exam_id: UUID,
        *,
        scheduled_date: date | None = None,
        part: int | None = None,
        exam_from: int | None = None,
        exam_to: int | None = None,
        notes: str | None = None,
        status: ExamStatus | None = None,
        clear: frozenset[str] = frozenset(),
    ) -> None:
        model = await self._session.get(UpcomingExamModel, exam_id)
        if model is None:  # pragma: no cover - guarded by the router
            return
        if scheduled_date is not None:
            model.scheduled_date = scheduled_date
        if status is not None:
            model.status = status.value
        # `clear` lets a caller blank an optional field, which `None` alone cannot
        # express (None also means "leave unchanged" here).
        for field, value in (
            ("part", part),
            ("exam_from", exam_from),
            ("exam_to", exam_to),
            ("notes", notes),
        ):
            if field in clear:
                setattr(model, field, None)
            elif value is not None:
                setattr(model, field, value)
        await self._session.flush()

    async def delete(self, exam_id: UUID) -> None:
        model = await self._session.get(UpcomingExamModel, exam_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
