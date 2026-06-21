"""Halaqahs domain layer.

A ``Halaqah`` (study circle) is led by a teacher, has a type and an optional
weekly time, and groups students. The number of students is **not stored** — it
is computed from the students enrolled in the halaqah and surfaced through the
:class:`HalaqahView` read model.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from institute_administration.shared.application.pagination import Page
from institute_administration.shared.domain import (
    AggregateRoot,
    ConflictError,
    EntityNotFoundError,
)


class Halaqah(AggregateRoot[UUID]):
    def __init__(
        self,
        *,
        id: UUID,
        name: str,
        teacher_id: UUID,
        halaqah_type_id: UUID,
        level: str | None = None,
        age: str | None = None,
        time_id: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.teacher_id = teacher_id
        self.halaqah_type_id = halaqah_type_id
        self.level = level
        self.age = age
        self.time_id = time_id
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(
        cls,
        *,
        name: str,
        teacher_id: UUID,
        halaqah_type_id: UUID,
        level: str | None = None,
        age: str | None = None,
        time_id: UUID | None = None,
    ) -> Halaqah:
        return cls(
            id=uuid4(),
            name=name.strip(),
            teacher_id=teacher_id,
            halaqah_type_id=halaqah_type_id,
            level=level,
            age=age,
            time_id=time_id,
        )


@dataclass(frozen=True)
class HalaqahView:
    """Read model: a halaqah with related names and its live student count."""

    id: UUID
    name: str
    level: str | None
    age: str | None
    teacher_id: UUID
    teacher_name: str
    halaqah_type_id: UUID
    halaqah_type_name: str
    time_id: UUID | None
    number_of_students: int
    created_at: datetime
    updated_at: datetime


class HalaqahRepository(ABC):
    @abstractmethod
    async def add(self, halaqah: Halaqah) -> None: ...

    @abstractmethod
    async def update(self, halaqah: Halaqah) -> None: ...

    @abstractmethod
    async def get_entity(self, halaqah_id: UUID) -> Halaqah | None: ...

    @abstractmethod
    async def get_view(self, halaqah_id: UUID) -> HalaqahView | None: ...

    @abstractmethod
    async def list_views(
        self, page: Page, *, teacher_id: UUID | None = None
    ) -> list[HalaqahView]: ...

    @abstractmethod
    async def count(self, *, teacher_id: UUID | None = None) -> int: ...

    @abstractmethod
    async def ids_for_teacher(self, teacher_id: UUID) -> set[UUID]: ...

    @abstractmethod
    async def delete(self, halaqah: Halaqah) -> None: ...


class HalaqahNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "الحلقة غير موجودة") -> None:
        super().__init__(message)


class InvalidHalaqahRelationError(ConflictError):
    def __init__(self, message: str = "تأكد من اختيار معلم ونوع ووقت صحيحين") -> None:
        super().__init__(message)
