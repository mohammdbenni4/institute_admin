"""Teachers presentation layer: CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from institute_administration.api.dependencies import DbSession
from institute_administration.modules.identity.dependencies import (
    CurrentSuperAdmin,
    CurrentUser,
    get_current_user,
)
from institute_administration.modules.identity.repository import SqlAlchemyUserRepository
from institute_administration.modules.teachers.repository import SqlAlchemyTeacherRepository
from institute_administration.modules.teachers.schemas import (
    TeacherCreateRequest,
    TeacherListResponse,
    TeacherResponse,
    TeacherUpdateRequest,
)
from institute_administration.modules.teachers.service import (
    CreateTeacherInput,
    TeacherService,
    UpdateTeacherInput,
)
from institute_administration.shared.application.pagination import Page


def get_service(session: DbSession) -> TeacherService:
    return TeacherService(
        SqlAlchemyTeacherRepository(session),
        SqlAlchemyUserRepository(session),
    )


ServiceDep = Annotated[TeacherService, Depends(get_service)]

router = APIRouter(
    prefix="/teachers",
    tags=["المعلمون"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=TeacherResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء معلم",
)
async def create(
    payload: TeacherCreateRequest, service: ServiceDep, _: CurrentSuperAdmin
) -> TeacherResponse:
    view = await service.create(
        CreateTeacherInput(
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            academic_study=payload.academic_study,
            islamic_study=payload.islamic_study,
            is_assistant=payload.is_assistant,
            date_of_birth=payload.date_of_birth,
        )
    )
    return TeacherResponse.from_view(view)


@router.get("", response_model=TeacherListResponse, summary="قائمة المعلمين")
async def list_(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TeacherListResponse:
    items, total = await service.list(Page(limit=limit, offset=offset))
    return TeacherListResponse(
        items=[TeacherResponse.from_view(v) for v in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/me", response_model=TeacherResponse, summary="ملف المعلم الحالي")
async def get_me(service: ServiceDep, current_user: CurrentUser) -> TeacherResponse:
    return TeacherResponse.from_view(await service.get_for_user(current_user.id))


@router.get("/{teacher_id}", response_model=TeacherResponse, summary="عرض معلم")
async def get(teacher_id: UUID, service: ServiceDep) -> TeacherResponse:
    return TeacherResponse.from_view(await service.get(teacher_id))


@router.patch("/{teacher_id}", response_model=TeacherResponse, summary="تعديل معلم")
async def update(
    teacher_id: UUID,
    payload: TeacherUpdateRequest,
    service: ServiceDep,
    _: CurrentSuperAdmin,
) -> TeacherResponse:
    data = payload.model_dump(exclude_unset=True)
    view = await service.update(teacher_id, UpdateTeacherInput(**data))
    return TeacherResponse.from_view(view)


@router.delete(
    "/{teacher_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف معلم",
)
async def delete(teacher_id: UUID, service: ServiceDep, _: CurrentSuperAdmin) -> None:
    await service.delete(teacher_id)
