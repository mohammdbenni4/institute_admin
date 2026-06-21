"""Students infrastructure: SQLAlchemy repository implementation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.core.config import get_settings
from institute_administration.modules.students.domain import (
    InvalidHalaqahError,
    Student,
    StudentRepository,
)
from institute_administration.modules.students.models import StudentModel
from institute_administration.shared.application.pagination import Page


def _to_entity(model: StudentModel) -> Student:
    return Student(
        id=model.id,
        full_name=model.full_name,
        father_name=model.father_name,
        father_number=model.father_number,
        date_of_birth=model.date_of_birth,
        mother_number=model.mother_number,
        orphan_of=model.orphan_of,
        residential_area=model.residential_area,
        accepted_at=model.accepted_at,
        notes=model.notes,
        halaqah_id=model.halaqah_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply(model: StudentModel, student: Student) -> None:
    model.full_name = student.full_name
    model.father_name = student.father_name
    model.father_number = student.father_number
    model.date_of_birth = student.date_of_birth
    model.mother_number = student.mother_number
    model.orphan_of = student.orphan_of
    model.residential_area = student.residential_area
    model.accepted_at = student.accepted_at
    model.notes = student.notes
    model.halaqah_id = student.halaqah_id


class SqlAlchemyStudentRepository(StudentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_collation = get_settings().arabic_collation

    async def add(self, student: Student) -> None:
        model = StudentModel(id=student.id)
        _apply(model, student)
        self._session.add(model)
        await self._flush()

    async def update(self, student: Student) -> None:
        model = await self._session.get(StudentModel, student.id)
        if model is None:  # pragma: no cover - guarded by the service layer
            return
        _apply(model, student)
        await self._flush()

    async def get_by_id(self, student_id: UUID) -> Student | None:
        model = await self._session.get(StudentModel, student_id)
        return _to_entity(model) if model else None

    async def list(
        self,
        page: Page,
        *,
        halaqah_id: UUID | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
    ) -> list[Student]:
        stmt = select(StudentModel)
        if halaqah_id is not None:
            stmt = stmt.where(StudentModel.halaqah_id == halaqah_id)
        if halaqah_ids is not None:
            stmt = stmt.where(StudentModel.halaqah_id.in_(halaqah_ids))
        stmt = (
            stmt.order_by(StudentModel.full_name.collate(self._order_collation))
            .limit(page.limit)
            .offset(page.offset)
        )
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def count(
        self, *, halaqah_id: UUID | None = None, halaqah_ids: frozenset[UUID] | None = None
    ) -> int:
        stmt = select(func.count()).select_from(StudentModel)
        if halaqah_id is not None:
            stmt = stmt.where(StudentModel.halaqah_id == halaqah_id)
        if halaqah_ids is not None:
            stmt = stmt.where(StudentModel.halaqah_id.in_(halaqah_ids))
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def delete(self, student: Student) -> None:
        model = await self._session.get(StudentModel, student.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def _flush(self) -> None:
        try:
            await self._session.flush()
        except IntegrityError as exc:  # bad halaqah_id (FK violation)
            raise InvalidHalaqahError from exc
