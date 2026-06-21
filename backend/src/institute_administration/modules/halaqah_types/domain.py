"""Halaqah-type domain layer: entity, repository port, and errors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID, uuid4

from institute_administration.shared.application.pagination import Page
from institute_administration.shared.domain import (
    AggregateRoot,
    ConflictError,
    EntityNotFoundError,
)


class HalaqahType(AggregateRoot[UUID]):
    """A category/type of halaqah (e.g. تحفيظ، تجويد)."""

    def __init__(
        self,
        *,
        id: UUID,
        name: str,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, *, name: str) -> HalaqahType:
        return cls(id=uuid4(), name=name.strip())

    def rename(self, name: str) -> None:
        self.name = name.strip()


class HalaqahTypeRepository(ABC):
    @abstractmethod
    async def add(self, halaqah_type: HalaqahType) -> None: ...

    @abstractmethod
    async def update(self, halaqah_type: HalaqahType) -> None: ...

    @abstractmethod
    async def get_by_id(self, type_id: UUID) -> HalaqahType | None: ...

    @abstractmethod
    async def exists_by_name(self, name: str, *, exclude_id: UUID | None = None) -> bool: ...

    @abstractmethod
    async def list(self, page: Page) -> list[HalaqahType]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def delete(self, halaqah_type: HalaqahType) -> None: ...


class HalaqahTypeNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "نوع الحلقة غير موجود") -> None:
        super().__init__(message)


class HalaqahTypeNameAlreadyExistsError(ConflictError):
    def __init__(self, message: str = "اسم نوع الحلقة مستخدم بالفعل") -> None:
        super().__init__(message)
