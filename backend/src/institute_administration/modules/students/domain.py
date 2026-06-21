"""Students domain layer.

A student is a child enrolled in a halaqah. Students never authenticate, so they
carry no credentials — only their guardians' contact details and enrolment data.
The halaqah is referenced by id only (it may be unassigned, i.e. ``None``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from institute_administration.shared.application.pagination import Page
from institute_administration.shared.domain import ConflictError, EntityNotFoundError
from institute_administration.shared.domain.aggregate_root import AggregateRoot


class OrphanStatus(StrEnum):
    """Which parent the student is orphaned of (``None`` means not orphaned)."""

    FATHER = "father"
    MOTHER = "mother"
    BOTH = "both"


class Student(AggregateRoot[UUID]):
    def __init__(
        self,
        *,
        id: UUID,
        full_name: str,
        father_name: str,
        father_number: str,
        date_of_birth: date | None = None,
        mother_number: str | None = None,
        orphan_of: OrphanStatus | None = None,
        residential_area: str | None = None,
        accepted_at: date | None = None,
        notes: str | None = None,
        halaqah_id: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.full_name = full_name
        self.father_name = father_name
        self.father_number = father_number
        self.date_of_birth = date_of_birth
        self.mother_number = mother_number
        self.orphan_of = orphan_of
        self.residential_area = residential_area
        self.accepted_at = accepted_at
        self.notes = notes
        self.halaqah_id = halaqah_id
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(
        cls,
        *,
        full_name: str,
        father_name: str,
        father_number: str,
        date_of_birth: date | None = None,
        mother_number: str | None = None,
        orphan_of: OrphanStatus | None = None,
        residential_area: str | None = None,
        accepted_at: date | None = None,
        notes: str | None = None,
        halaqah_id: UUID | None = None,
    ) -> Student:
        return cls(
            id=uuid4(),
            full_name=full_name.strip(),
            father_name=father_name.strip(),
            father_number=father_number.strip(),
            date_of_birth=date_of_birth,
            mother_number=mother_number,
            orphan_of=orphan_of,
            residential_area=residential_area,
            accepted_at=accepted_at,
            notes=notes,
            halaqah_id=halaqah_id,
        )


class StudentRepository(ABC):
    @abstractmethod
    async def add(self, student: Student) -> None: ...

    @abstractmethod
    async def update(self, student: Student) -> None: ...

    @abstractmethod
    async def get_by_id(self, student_id: UUID) -> Student | None: ...

    @abstractmethod
    async def list(
        self,
        page: Page,
        *,
        halaqah_id: UUID | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
    ) -> list[Student]: ...

    @abstractmethod
    async def count(
        self, *, halaqah_id: UUID | None = None, halaqah_ids: frozenset[UUID] | None = None
    ) -> int: ...

    @abstractmethod
    async def delete(self, student: Student) -> None: ...


class StudentNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "الطالب غير موجود") -> None:
        super().__init__(message)


class InvalidHalaqahError(ConflictError):
    def __init__(self, message: str = "الحلقة المحددة غير موجودة") -> None:
        super().__init__(message)
