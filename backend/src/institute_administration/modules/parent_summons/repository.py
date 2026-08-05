"""Parent summons infrastructure: SQLAlchemy repository.

Every list query resolves the student, teacher and halaqah names in the same
statement, so the admin table can link to each profile and offer a WhatsApp
button without an extra request per row.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.modules.halaqahs.models import HalaqahModel
from institute_administration.modules.identity.models import UserModel
from institute_administration.modules.parent_summons.domain import (
    ParentSummonView,
    SummonStatus,
)
from institute_administration.modules.parent_summons.models import ParentSummonModel
from institute_administration.modules.students.models import StudentModel
from institute_administration.modules.teachers.models import TeacherModel
from institute_administration.shared.application.pagination import Page


def _view(row: tuple) -> ParentSummonView:  # type: ignore[type-arg]
    model, student_name, father_name, father_number, teacher_name, halaqah_name = row
    return ParentSummonView(
        id=model.id,
        student_id=model.student_id,
        student_name=student_name,
        father_name=father_name,
        father_number=father_number,
        teacher_id=model.teacher_id,
        teacher_name=teacher_name,
        halaqah_id=model.halaqah_id,
        halaqah_name=halaqah_name,
        reason=model.reason,
        status=SummonStatus(model.status),
        admin_response=model.admin_response,
        handled_at=model.handled_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyParentSummonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _view_select(self) -> Select[tuple]:  # type: ignore[type-arg]
        return (
            select(
                ParentSummonModel,
                StudentModel.full_name,
                StudentModel.father_name,
                StudentModel.father_number,
                UserModel.full_name,
                HalaqahModel.name,
            )
            .join(StudentModel, ParentSummonModel.student_id == StudentModel.id)
            .join(TeacherModel, ParentSummonModel.teacher_id == TeacherModel.id)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .join(HalaqahModel, ParentSummonModel.halaqah_id == HalaqahModel.id)
        )

    def _filtered(
        self,
        stmt: Select[tuple],  # type: ignore[type-arg]
        *,
        status: SummonStatus | None,
        student_id: UUID | None,
        teacher_id: UUID | None,
        halaqah_ids: frozenset[UUID] | None,
    ) -> Select[tuple]:  # type: ignore[type-arg]
        if status is not None:
            stmt = stmt.where(ParentSummonModel.status == status.value)
        if student_id is not None:
            stmt = stmt.where(ParentSummonModel.student_id == student_id)
        if teacher_id is not None:
            stmt = stmt.where(ParentSummonModel.teacher_id == teacher_id)
        if halaqah_ids is not None:
            stmt = stmt.where(ParentSummonModel.halaqah_id.in_(halaqah_ids))
        return stmt

    async def add(
        self, *, student_id: UUID, teacher_id: UUID, halaqah_id: UUID, reason: str
    ) -> UUID:
        model = ParentSummonModel(
            id=uuid4(),
            student_id=student_id,
            teacher_id=teacher_id,
            halaqah_id=halaqah_id,
            reason=reason,
            status=SummonStatus.NEW.value,
        )
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def get_view(self, summon_id: UUID) -> ParentSummonView | None:
        result = await self._session.execute(
            self._view_select().where(ParentSummonModel.id == summon_id)
        )
        row = result.first()
        return _view(tuple(row)) if row else None

    async def list_views(
        self,
        page: Page,
        *,
        status: SummonStatus | None = None,
        student_id: UUID | None = None,
        teacher_id: UUID | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
    ) -> list[ParentSummonView]:
        stmt = self._filtered(
            self._view_select(),
            status=status,
            student_id=student_id,
            teacher_id=teacher_id,
            halaqah_ids=halaqah_ids,
        )
        # Newest first: the admin works the queue from the top.
        result = await self._session.execute(
            stmt.order_by(ParentSummonModel.created_at.desc()).limit(page.limit).offset(page.offset)
        )
        return [_view(tuple(row)) for row in result.all()]

    async def count(
        self,
        *,
        status: SummonStatus | None = None,
        student_id: UUID | None = None,
        teacher_id: UUID | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
    ) -> int:
        stmt = self._filtered(
            select(func.count()).select_from(ParentSummonModel),
            status=status,
            student_id=student_id,
            teacher_id=teacher_id,
            halaqah_ids=halaqah_ids,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_by_status(
        self, *, halaqah_ids: frozenset[UUID] | None = None
    ) -> dict[SummonStatus, int]:
        """Queue sizes for the admin badge and the teacher's panel header."""
        stmt = select(ParentSummonModel.status, func.count()).group_by(ParentSummonModel.status)
        if halaqah_ids is not None:
            stmt = stmt.where(ParentSummonModel.halaqah_id.in_(halaqah_ids))
        rows = await self._session.execute(stmt)
        counts = dict.fromkeys(SummonStatus, 0)
        for value, total in rows:
            counts[SummonStatus(value)] = int(total)
        return counts

    async def update(
        self,
        summon_id: UUID,
        *,
        status: SummonStatus | None = None,
        admin_response: str | None = None,
    ) -> None:
        model = await self._session.get(ParentSummonModel, summon_id)
        if model is None:  # pragma: no cover - guarded by the router
            return
        if status is not None:
            model.status = status.value
            # Stamp the moment the administration closed the matter.
            model.handled_at = (
                datetime.now(UTC) if status is SummonStatus.COMPLETED else model.handled_at
            )
        if admin_response is not None:
            model.admin_response = admin_response
        await self._session.flush()

    async def delete(self, summon_id: UUID) -> None:
        model = await self._session.get(ParentSummonModel, summon_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
