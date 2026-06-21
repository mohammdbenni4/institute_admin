"""Teachers domain layer.

A ``Teacher`` is the professional profile attached one-to-one to a ``User`` whose
role is ``teacher``. The teacher aggregate references the user by id only; user
details are composed into a :class:`TeacherView` read model for queries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid4

from institute_administration.shared.application.pagination import Page
from institute_administration.shared.domain import (
    AggregateRoot,
    ConflictError,
    EntityNotFoundError,
)


class Teacher(AggregateRoot[UUID]):
    """The teaching profile of a user."""

    def __init__(
        self,
        *,
        id: UUID,
        user_id: UUID,
        academic_study: str,
        islamic_study: str,
        is_assistant: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.user_id = user_id
        self.academic_study = academic_study
        self.islamic_study = islamic_study
        self.is_assistant = is_assistant
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        academic_study: str,
        islamic_study: str,
        is_assistant: bool = False,
    ) -> Teacher:
        return cls(
            id=uuid4(),
            user_id=user_id,
            academic_study=academic_study.strip(),
            islamic_study=islamic_study.strip(),
            is_assistant=is_assistant,
        )

    def set_academic_study(self, value: str) -> None:
        self.academic_study = value.strip()

    def set_islamic_study(self, value: str) -> None:
        self.islamic_study = value.strip()

    def set_is_assistant(self, value: bool) -> None:
        self.is_assistant = value


@dataclass(frozen=True)
class TeacherView:
    """Read model: a teacher joined with its user's identity fields."""

    id: UUID
    user_id: UUID
    full_name: str
    email: str
    date_of_birth: date | None
    is_active: bool
    academic_study: str
    islamic_study: str
    is_assistant: bool
    created_at: datetime
    updated_at: datetime


class TeacherRepository(ABC):
    @abstractmethod
    async def add(self, teacher: Teacher) -> None: ...

    @abstractmethod
    async def update(self, teacher: Teacher) -> None: ...

    @abstractmethod
    async def get_entity(self, teacher_id: UUID) -> Teacher | None: ...

    @abstractmethod
    async def get_view(self, teacher_id: UUID) -> TeacherView | None: ...

    @abstractmethod
    async def get_view_by_user_id(self, user_id: UUID) -> TeacherView | None: ...

    @abstractmethod
    async def exists_by_user_id(self, user_id: UUID) -> bool: ...

    @abstractmethod
    async def list_views(self, page: Page) -> list[TeacherView]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def delete(self, teacher: Teacher) -> None: ...


class TeacherNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "المعلم غير موجود") -> None:
        super().__init__(message)


class UserAlreadyTeacherError(ConflictError):
    def __init__(self, message: str = "هذا المستخدم معلم بالفعل") -> None:
        super().__init__(message)


class TeacherInUseError(ConflictError):
    def __init__(self, message: str = "لا يمكن حذف المعلم لارتباطه بحلقات") -> None:
        super().__init__(message)
