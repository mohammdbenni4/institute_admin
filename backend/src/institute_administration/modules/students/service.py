"""Students application layer: CRUD use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from institute_administration.modules.students.domain import (
    OrphanStatus,
    Student,
    StudentNotFoundError,
    StudentRepository,
)
from institute_administration.shared.application.pagination import Page
from institute_administration.shared.application.sentinels import UNSET, Unset


@dataclass(frozen=True)
class CreateStudentInput:
    full_name: str
    father_name: str
    father_number: str
    date_of_birth: date | None = None
    mother_number: str | None = None
    orphan_of: OrphanStatus | None = None
    residential_area: str | None = None
    accepted_at: date | None = None
    notes: str | None = None
    halaqah_id: UUID | None = None


@dataclass(frozen=True)
class UpdateStudentInput:
    full_name: str | Unset = UNSET
    father_name: str | Unset = UNSET
    father_number: str | Unset = UNSET
    date_of_birth: date | None | Unset = UNSET
    mother_number: str | None | Unset = UNSET
    orphan_of: OrphanStatus | None | Unset = UNSET
    residential_area: str | None | Unset = UNSET
    accepted_at: date | None | Unset = UNSET
    notes: str | None | Unset = UNSET
    halaqah_id: UUID | None | Unset = UNSET


class StudentService:
    def __init__(self, students: StudentRepository) -> None:
        self._students = students

    async def create(self, data: CreateStudentInput) -> Student:
        student = Student.create(
            full_name=data.full_name,
            father_name=data.father_name,
            father_number=data.father_number,
            date_of_birth=data.date_of_birth,
            mother_number=data.mother_number,
            orphan_of=data.orphan_of,
            residential_area=data.residential_area,
            accepted_at=data.accepted_at,
            notes=data.notes,
            halaqah_id=data.halaqah_id,
        )
        await self._students.add(student)
        return await self.get(student.id)

    async def create_many(self, items: list[CreateStudentInput]) -> int:
        """Create many students in the current unit of work. Returns the count.

        All rows share the request transaction, so the import is atomic: if any
        row violates a constraint the whole batch is rolled back.
        """
        for data in items:
            student = Student.create(
                full_name=data.full_name,
                father_name=data.father_name,
                father_number=data.father_number,
                date_of_birth=data.date_of_birth,
                mother_number=data.mother_number,
                orphan_of=data.orphan_of,
                residential_area=data.residential_area,
                accepted_at=data.accepted_at,
                notes=data.notes,
                halaqah_id=data.halaqah_id,
            )
            await self._students.add(student)
        return len(items)

    async def get(self, student_id: UUID) -> Student:
        student = await self._students.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError
        return student

    async def list(
        self,
        page: Page,
        *,
        halaqah_id: UUID | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
    ) -> tuple[list[Student], int]:
        students = await self._students.list(page, halaqah_id=halaqah_id, halaqah_ids=halaqah_ids)
        total = await self._students.count(halaqah_id=halaqah_id, halaqah_ids=halaqah_ids)
        return students, total

    async def update(self, student_id: UUID, data: UpdateStudentInput) -> Student:
        student = await self.get(student_id)
        if data.full_name is not UNSET:
            student.full_name = data.full_name.strip()
        if data.father_name is not UNSET:
            student.father_name = data.father_name.strip()
        if data.father_number is not UNSET:
            student.father_number = data.father_number.strip()
        if data.date_of_birth is not UNSET:
            student.date_of_birth = data.date_of_birth
        if data.mother_number is not UNSET:
            student.mother_number = data.mother_number
        if data.orphan_of is not UNSET:
            student.orphan_of = data.orphan_of
        if data.residential_area is not UNSET:
            student.residential_area = data.residential_area
        if data.accepted_at is not UNSET:
            student.accepted_at = data.accepted_at
        if data.notes is not UNSET:
            student.notes = data.notes
        if data.halaqah_id is not UNSET:
            student.halaqah_id = data.halaqah_id
        await self._students.update(student)
        return await self.get(student_id)

    async def delete(self, student_id: UUID) -> None:
        student = await self.get(student_id)
        await self._students.delete(student)
