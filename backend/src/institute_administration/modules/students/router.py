"""Students presentation layer: CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from institute_administration.api.dependencies import DbSession
from institute_administration.api.scoping import ScopeDep
from institute_administration.modules.identity.dependencies import (
    CurrentSuperAdmin,
    get_current_user,
)
from institute_administration.modules.students.domain import StudentNotFoundError, StudentRepository
from institute_administration.modules.students.repository import SqlAlchemyStudentRepository
from institute_administration.modules.students.schemas import (
    StudentCreateRequest,
    StudentImportRequest,
    StudentImportResponse,
    StudentListResponse,
    StudentResponse,
    StudentUpdateRequest,
)
from institute_administration.modules.students.service import (
    CreateStudentInput,
    StudentService,
    UpdateStudentInput,
)
from institute_administration.shared.application.pagination import Page


def get_repository(session: DbSession) -> StudentRepository:
    return SqlAlchemyStudentRepository(session)


def get_service(
    repository: Annotated[StudentRepository, Depends(get_repository)],
) -> StudentService:
    return StudentService(repository)


ServiceDep = Annotated[StudentService, Depends(get_service)]

router = APIRouter(
    prefix="/students",
    tags=["الطلاب"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء طالب",
)
async def create(
    payload: StudentCreateRequest, service: ServiceDep, _: CurrentSuperAdmin
) -> StudentResponse:
    student = await service.create(CreateStudentInput(**payload.model_dump()))
    return StudentResponse.from_entity(student)


@router.post(
    "/import",
    response_model=StudentImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="استيراد طلاب دفعة واحدة",
)
async def import_students(
    payload: StudentImportRequest, service: ServiceDep, _: CurrentSuperAdmin
) -> StudentImportResponse:
    created = await service.create_many(
        [CreateStudentInput(**item.model_dump()) for item in payload.items]
    )
    return StudentImportResponse(created=created)


@router.get("", response_model=StudentListResponse, summary="قائمة الطلاب")
async def list_(
    service: ServiceDep,
    scope: ScopeDep,
    halaqah_id: Annotated[UUID | None, Query(description="تصفية حسب الحلقة")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> StudentListResponse:
    empty = StudentListResponse(items=[], total=0, limit=limit, offset=offset)
    restrict: frozenset[UUID] | None = None
    if not scope.is_admin:
        if not scope.halaqah_ids:
            return empty
        if halaqah_id is not None and not scope.allows_halaqah(halaqah_id):
            return empty
        restrict = scope.halaqah_ids
    items, total = await service.list(
        Page(limit=limit, offset=offset), halaqah_id=halaqah_id, halaqah_ids=restrict
    )
    return StudentListResponse(
        items=[StudentResponse.from_entity(s) for s in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{student_id}", response_model=StudentResponse, summary="عرض طالب")
async def get(student_id: UUID, service: ServiceDep, scope: ScopeDep) -> StudentResponse:
    student = await service.get(student_id)
    if not scope.allows_halaqah(student.halaqah_id):
        raise StudentNotFoundError
    return StudentResponse.from_entity(student)


@router.patch("/{student_id}", response_model=StudentResponse, summary="تعديل طالب")
async def update(
    student_id: UUID,
    payload: StudentUpdateRequest,
    service: ServiceDep,
    _: CurrentSuperAdmin,
) -> StudentResponse:
    data = payload.model_dump(exclude_unset=True)
    student = await service.update(student_id, UpdateStudentInput(**data))
    return StudentResponse.from_entity(student)


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف طالب",
)
async def delete(student_id: UUID, service: ServiceDep, _: CurrentSuperAdmin) -> None:
    await service.delete(student_id)
