"""Teachers application layer.

Coordinates the identity context (the underlying ``User``) and the teachers
context (the ``Teacher`` profile) within a single transaction, so that "add
teacher" creates both the login account and the profile atomically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from institute_administration.core.security import hash_password
from institute_administration.modules.identity.domain import (
    EmailAlreadyExistsError,
    RawPassword,
    User,
    UserRepository,
    UserRole,
)
from institute_administration.modules.teachers.domain import (
    Teacher,
    TeacherNotFoundError,
    TeacherRepository,
    TeacherView,
)
from institute_administration.shared.application.pagination import Page
from institute_administration.shared.application.sentinels import UNSET, Unset


@dataclass(frozen=True)
class CreateTeacherInput:
    full_name: str
    email: str
    password: str
    academic_study: str
    islamic_study: str
    is_assistant: bool = False
    date_of_birth: date | None = None


@dataclass(frozen=True)
class UpdateTeacherInput:
    full_name: str | Unset = UNSET
    email: str | Unset = UNSET
    password: str | Unset = UNSET
    date_of_birth: date | None | Unset = UNSET
    is_active: bool | Unset = UNSET
    academic_study: str | Unset = UNSET
    islamic_study: str | Unset = UNSET
    is_assistant: bool | Unset = UNSET


class TeacherService:
    def __init__(self, teachers: TeacherRepository, users: UserRepository) -> None:
        self._teachers = teachers
        self._users = users

    async def create(self, data: CreateTeacherInput) -> TeacherView:
        if await self._users.exists_by_email(data.email):
            raise EmailAlreadyExistsError
        user = User.create(
            full_name=data.full_name,
            email=data.email,
            password_hash=hash_password(RawPassword(data.password).value),
            role=UserRole.TEACHER,
            date_of_birth=data.date_of_birth,
        )
        await self._users.add(user)
        teacher = Teacher.create(
            user_id=user.id,
            academic_study=data.academic_study,
            islamic_study=data.islamic_study,
            is_assistant=data.is_assistant,
        )
        await self._teachers.add(teacher)
        return await self._require_view(teacher.id)

    async def get(self, teacher_id: UUID) -> TeacherView:
        return await self._require_view(teacher_id)

    async def get_for_user(self, user_id: UUID) -> TeacherView:
        view = await self._teachers.get_view_by_user_id(user_id)
        if view is None:
            raise TeacherNotFoundError
        return view

    async def list(self, page: Page) -> tuple[list[TeacherView], int]:
        return await self._teachers.list_views(page), await self._teachers.count()

    async def update(self, teacher_id: UUID, data: UpdateTeacherInput) -> TeacherView:
        teacher = await self._teachers.get_entity(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError
        user = await self._users.get_by_id(teacher.user_id)
        if user is None:  # pragma: no cover - referential integrity guarantees a user
            raise TeacherNotFoundError

        await self._apply_user_changes(user, data)
        if data.academic_study is not UNSET:
            teacher.set_academic_study(data.academic_study)
        if data.islamic_study is not UNSET:
            teacher.set_islamic_study(data.islamic_study)
        if data.is_assistant is not UNSET:
            teacher.set_is_assistant(data.is_assistant)
        await self._teachers.update(teacher)

        return await self._require_view(teacher_id)

    async def delete(self, teacher_id: UUID) -> None:
        teacher = await self._teachers.get_entity(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError
        user = await self._users.get_by_id(teacher.user_id)
        await self._teachers.delete(teacher)  # raises if referenced by halaqahs
        if user is not None:
            await self._users.delete(user)

    async def _apply_user_changes(self, user: User, data: UpdateTeacherInput) -> None:
        if data.email is not UNSET and data.email != user.email.value:
            if await self._users.exists_by_email(data.email, exclude_id=user.id):
                raise EmailAlreadyExistsError
            user.change_email(data.email)
        if data.full_name is not UNSET:
            user.rename(data.full_name)
        if data.password is not UNSET:
            user.set_password_hash(hash_password(RawPassword(data.password).value))
        if data.date_of_birth is not UNSET:
            user.set_date_of_birth(data.date_of_birth)
        if data.is_active is not UNSET:
            user.activate() if data.is_active else user.deactivate()
        await self._users.update(user)

    async def _require_view(self, teacher_id: UUID) -> TeacherView:
        view = await self._teachers.get_view(teacher_id)
        if view is None:
            raise TeacherNotFoundError
        return view
