"""Teachers infrastructure: SQLAlchemy repository implementation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.core.config import get_settings
from institute_administration.modules.identity.models import UserModel
from institute_administration.modules.teachers.domain import (
    Teacher,
    TeacherInUseError,
    TeacherRepository,
    TeacherView,
)
from institute_administration.modules.teachers.models import TeacherModel
from institute_administration.shared.application.pagination import Page


def _entity(model: TeacherModel) -> Teacher:
    return Teacher(
        id=model.id,
        user_id=model.user_id,
        academic_study=model.academic_study,
        islamic_study=model.islamic_study,
        is_assistant=model.is_assistant,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _view(teacher: TeacherModel, user: UserModel) -> TeacherView:
    return TeacherView(
        id=teacher.id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        date_of_birth=user.date_of_birth,
        is_active=user.is_active,
        academic_study=teacher.academic_study,
        islamic_study=teacher.islamic_study,
        is_assistant=teacher.is_assistant,
        created_at=teacher.created_at,
        updated_at=teacher.updated_at,
    )


class SqlAlchemyTeacherRepository(TeacherRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_collation = get_settings().arabic_collation

    async def add(self, teacher: Teacher) -> None:
        self._session.add(
            TeacherModel(
                id=teacher.id,
                user_id=teacher.user_id,
                academic_study=teacher.academic_study,
                islamic_study=teacher.islamic_study,
                is_assistant=teacher.is_assistant,
            )
        )
        await self._session.flush()

    async def update(self, teacher: Teacher) -> None:
        model = await self._session.get(TeacherModel, teacher.id)
        if model is None:  # pragma: no cover - guarded by the service layer
            return
        model.academic_study = teacher.academic_study
        model.islamic_study = teacher.islamic_study
        model.is_assistant = teacher.is_assistant
        await self._session.flush()

    async def get_entity(self, teacher_id: UUID) -> Teacher | None:
        model = await self._session.get(TeacherModel, teacher_id)
        return _entity(model) if model else None

    async def get_view(self, teacher_id: UUID) -> TeacherView | None:
        result = await self._session.execute(
            select(TeacherModel, UserModel)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .where(TeacherModel.id == teacher_id)
        )
        row = result.first()
        return _view(row[0], row[1]) if row else None

    async def get_view_by_user_id(self, user_id: UUID) -> TeacherView | None:
        result = await self._session.execute(
            select(TeacherModel, UserModel)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .where(TeacherModel.user_id == user_id)
        )
        row = result.first()
        return _view(row[0], row[1]) if row else None

    async def exists_by_user_id(self, user_id: UUID) -> bool:
        result = await self._session.execute(
            select(TeacherModel.id).where(TeacherModel.user_id == user_id).limit(1)
        )
        return result.first() is not None

    async def list_views(self, page: Page) -> list[TeacherView]:
        result = await self._session.execute(
            select(TeacherModel, UserModel)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .order_by(UserModel.full_name.collate(self._order_collation))
            .limit(page.limit)
            .offset(page.offset)
        )
        return [_view(teacher, user) for teacher, user in result.all()]

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(TeacherModel))
        return int(result.scalar_one())

    async def delete(self, teacher: Teacher) -> None:
        model = await self._session.get(TeacherModel, teacher.id)
        if model is None:
            return
        await self._session.delete(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:  # referenced by halaqahs (ON DELETE RESTRICT)
            raise TeacherInUseError from exc
