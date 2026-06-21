"""Halaqah-type presentation layer: CRUD endpoints.

Reads are available to any authenticated user; writes require a super admin.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from institute_administration.api.dependencies import DbSession
from institute_administration.modules.halaqah_types.domain import HalaqahTypeRepository
from institute_administration.modules.halaqah_types.repository import (
    SqlAlchemyHalaqahTypeRepository,
)
from institute_administration.modules.halaqah_types.schemas import (
    HalaqahTypeCreateRequest,
    HalaqahTypeListResponse,
    HalaqahTypeResponse,
    HalaqahTypeUpdateRequest,
)
from institute_administration.modules.halaqah_types.service import (
    CreateHalaqahTypeInput,
    HalaqahTypeService,
    UpdateHalaqahTypeInput,
)
from institute_administration.modules.identity.dependencies import (
    CurrentSuperAdmin,
    get_current_user,
)
from institute_administration.shared.application.pagination import Page


def get_repository(session: DbSession) -> HalaqahTypeRepository:
    return SqlAlchemyHalaqahTypeRepository(session)


def get_service(
    repository: Annotated[HalaqahTypeRepository, Depends(get_repository)],
) -> HalaqahTypeService:
    return HalaqahTypeService(repository)


ServiceDep = Annotated[HalaqahTypeService, Depends(get_service)]

router = APIRouter(
    prefix="/halaqah-types",
    tags=["أنواع الحلقات"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=HalaqahTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء نوع حلقة",
)
async def create(
    payload: HalaqahTypeCreateRequest, service: ServiceDep, _: CurrentSuperAdmin
) -> HalaqahTypeResponse:
    halaqah_type = await service.create(CreateHalaqahTypeInput(name=payload.name))
    return HalaqahTypeResponse.from_entity(halaqah_type)


@router.get("", response_model=HalaqahTypeListResponse, summary="قائمة أنواع الحلقات")
async def list_(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HalaqahTypeListResponse:
    items, total = await service.list(Page(limit=limit, offset=offset))
    return HalaqahTypeListResponse(
        items=[HalaqahTypeResponse.from_entity(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{type_id}", response_model=HalaqahTypeResponse, summary="عرض نوع حلقة")
async def get(type_id: UUID, service: ServiceDep) -> HalaqahTypeResponse:
    return HalaqahTypeResponse.from_entity(await service.get(type_id))


@router.patch("/{type_id}", response_model=HalaqahTypeResponse, summary="تعديل نوع حلقة")
async def update(
    type_id: UUID,
    payload: HalaqahTypeUpdateRequest,
    service: ServiceDep,
    _: CurrentSuperAdmin,
) -> HalaqahTypeResponse:
    data = payload.model_dump(exclude_unset=True)
    halaqah_type = await service.update(type_id, UpdateHalaqahTypeInput(**data))
    return HalaqahTypeResponse.from_entity(halaqah_type)


@router.delete(
    "/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف نوع حلقة",
)
async def delete(type_id: UUID, service: ServiceDep, _: CurrentSuperAdmin) -> None:
    await service.delete(type_id)
