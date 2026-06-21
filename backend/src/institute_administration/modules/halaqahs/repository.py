"""Halaqahs infrastructure: SQLAlchemy repository implementation.

The view queries join the teacher (via its user) and the halaqah type for their
display names, and compute the live student count with a correlated subquery.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.core.config import get_settings
from institute_administration.modules.halaqah_types.models import HalaqahTypeModel
from institute_administration.modules.halaqahs.domain import (
    Halaqah,
    HalaqahRepository,
    HalaqahView,
    InvalidHalaqahRelationError,
)
from institute_administration.modules.halaqahs.models import HalaqahModel
from institute_administration.modules.identity.models import UserModel
from institute_administration.modules.students.models import StudentModel
from institute_administration.modules.teachers.models import TeacherModel
from institute_administration.shared.application.pagination import Page

_student_count = (
    select(func.count(StudentModel.id))
    .where(StudentModel.halaqah_id == HalaqahModel.id)
    .correlate(HalaqahModel)
    .scalar_subquery()
)


def _entity(model: HalaqahModel) -> Halaqah:
    return Halaqah(
        id=model.id,
        name=model.name,
        teacher_id=model.teacher_id,
        halaqah_type_id=model.halaqah_type_id,
        level=model.level,
        age=model.age,
        time_id=model.time_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _view(model: HalaqahModel, teacher_name: str, type_name: str, count: int) -> HalaqahView:
    return HalaqahView(
        id=model.id,
        name=model.name,
        level=model.level,
        age=model.age,
        teacher_id=model.teacher_id,
        teacher_name=teacher_name,
        halaqah_type_id=model.halaqah_type_id,
        halaqah_type_name=type_name,
        time_id=model.time_id,
        number_of_students=count,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyHalaqahRepository(HalaqahRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_collation = get_settings().arabic_collation

    def _view_select(self) -> Select[tuple[HalaqahModel, str, str, int]]:
        return (
            select(
                HalaqahModel,
                UserModel.full_name,
                HalaqahTypeModel.name,
                _student_count.label("number_of_students"),
            )
            .join(TeacherModel, HalaqahModel.teacher_id == TeacherModel.id)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .join(HalaqahTypeModel, HalaqahModel.halaqah_type_id == HalaqahTypeModel.id)
        )

    async def add(self, halaqah: Halaqah) -> None:
        self._session.add(
            HalaqahModel(
                id=halaqah.id,
                name=halaqah.name,
                teacher_id=halaqah.teacher_id,
                halaqah_type_id=halaqah.halaqah_type_id,
                level=halaqah.level,
                age=halaqah.age,
                time_id=halaqah.time_id,
            )
        )
        await self._flush()

    async def update(self, halaqah: Halaqah) -> None:
        model = await self._session.get(HalaqahModel, halaqah.id)
        if model is None:  # pragma: no cover - guarded by the service layer
            return
        model.name = halaqah.name
        model.teacher_id = halaqah.teacher_id
        model.halaqah_type_id = halaqah.halaqah_type_id
        model.level = halaqah.level
        model.age = halaqah.age
        model.time_id = halaqah.time_id
        await self._flush()

    async def get_entity(self, halaqah_id: UUID) -> Halaqah | None:
        model = await self._session.get(HalaqahModel, halaqah_id)
        return _entity(model) if model else None

    async def get_view(self, halaqah_id: UUID) -> HalaqahView | None:
        result = await self._session.execute(
            self._view_select().where(HalaqahModel.id == halaqah_id)
        )
        row = result.first()
        return _view(row[0], row[1], row[2], row[3]) if row else None

    async def list_views(self, page: Page, *, teacher_id: UUID | None = None) -> list[HalaqahView]:
        stmt = self._view_select()
        if teacher_id is not None:
            stmt = stmt.where(HalaqahModel.teacher_id == teacher_id)
        result = await self._session.execute(
            stmt.order_by(HalaqahModel.name.collate(self._order_collation))
            .limit(page.limit)
            .offset(page.offset)
        )
        return [_view(row[0], row[1], row[2], row[3]) for row in result.all()]

    async def count(self, *, teacher_id: UUID | None = None) -> int:
        stmt = select(func.count()).select_from(HalaqahModel)
        if teacher_id is not None:
            stmt = stmt.where(HalaqahModel.teacher_id == teacher_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def ids_for_teacher(self, teacher_id: UUID) -> set[UUID]:
        result = await self._session.execute(
            select(HalaqahModel.id).where(HalaqahModel.teacher_id == teacher_id)
        )
        return set(result.scalars().all())

    async def delete(self, halaqah: Halaqah) -> None:
        model = await self._session.get(HalaqahModel, halaqah.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def _flush(self) -> None:
        try:
            await self._session.flush()
        except IntegrityError as exc:  # bad teacher_id / halaqah_type_id / time_id
            raise InvalidHalaqahRelationError from exc
