"""Halaqahs presentation layer: CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from institute_administration.api.dependencies import DbSession
from institute_administration.api.scoping import ScopeDep
from institute_administration.modules.halaqahs.domain import HalaqahNotFoundError, HalaqahRepository
from institute_administration.modules.halaqahs.repository import SqlAlchemyHalaqahRepository
from institute_administration.modules.halaqahs.schemas import (
    HalaqahCreateRequest,
    HalaqahListResponse,
    HalaqahResponse,
    HalaqahUpdateRequest,
)
from institute_administration.modules.halaqahs.service import (
    CreateHalaqahInput,
    HalaqahService,
    UpdateHalaqahInput,
)
from institute_administration.modules.identity.dependencies import (
    CurrentSuperAdmin,
    get_current_user,
)
from institute_administration.shared.application.pagination import Page


def get_repository(session: DbSession) -> HalaqahRepository:
    return SqlAlchemyHalaqahRepository(session)


def get_service(
    repository: Annotated[HalaqahRepository, Depends(get_repository)],
) -> HalaqahService:
    return HalaqahService(repository)


ServiceDep = Annotated[HalaqahService, Depends(get_service)]

router = APIRouter(
    prefix="/halaqahs",
    tags=["الحلقات"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=HalaqahResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء حلقة",
)
async def create(
    payload: HalaqahCreateRequest, service: ServiceDep, _: CurrentSuperAdmin
) -> HalaqahResponse:
    view = await service.create(CreateHalaqahInput(**payload.model_dump()))
    return HalaqahResponse.from_view(view)


@router.get("", response_model=HalaqahListResponse, summary="قائمة الحلقات")
async def list_(
    service: ServiceDep,
    scope: ScopeDep,
    teacher_id: Annotated[UUID | None, Query(description="تصفية حسب المعلم")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HalaqahListResponse:
    if not scope.is_admin:
        if scope.teacher_id is None:
            return HalaqahListResponse(items=[], total=0, limit=limit, offset=offset)
        teacher_id = scope.teacher_id  # teachers see only their own halaqahs
    items, total = await service.list(Page(limit=limit, offset=offset), teacher_id=teacher_id)
    return HalaqahListResponse(
        items=[HalaqahResponse.from_view(v) for v in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{halaqah_id}", response_model=HalaqahResponse, summary="عرض حلقة")
async def get(halaqah_id: UUID, service: ServiceDep, scope: ScopeDep) -> HalaqahResponse:
    if not scope.allows_halaqah(halaqah_id):
        raise HalaqahNotFoundError
    return HalaqahResponse.from_view(await service.get(halaqah_id))


@router.patch("/{halaqah_id}", response_model=HalaqahResponse, summary="تعديل حلقة")
async def update(
    halaqah_id: UUID,
    payload: HalaqahUpdateRequest,
    service: ServiceDep,
    _: CurrentSuperAdmin,
) -> HalaqahResponse:
    data = payload.model_dump(exclude_unset=True)
    view = await service.update(halaqah_id, UpdateHalaqahInput(**data))
    return HalaqahResponse.from_view(view)


@router.delete(
    "/{halaqah_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف حلقة",
)
async def delete(halaqah_id: UUID, service: ServiceDep, _: CurrentSuperAdmin) -> None:
    await service.delete(halaqah_id)
