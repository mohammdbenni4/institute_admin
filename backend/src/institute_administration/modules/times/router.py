"""Times presentation layer: CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from institute_administration.api.dependencies import DbSession
from institute_administration.modules.identity.dependencies import (
    CurrentSuperAdmin,
    get_current_user,
)
from institute_administration.modules.times.domain import WEEKDAYS, DaySchedule, TimeRepository
from institute_administration.modules.times.repository import SqlAlchemyTimeRepository
from institute_administration.modules.times.schemas import (
    TimeCreateRequest,
    TimeListResponse,
    TimeResponse,
    TimeUpdateRequest,
)
from institute_administration.modules.times.service import (
    CreateTimeInput,
    TimeService,
    UpdateTimeInput,
)
from institute_administration.shared.application.pagination import Page
from institute_administration.shared.application.sentinels import UNSET


def get_repository(session: DbSession) -> TimeRepository:
    return SqlAlchemyTimeRepository(session)


def get_service(repository: Annotated[TimeRepository, Depends(get_repository)]) -> TimeService:
    return TimeService(repository)


ServiceDep = Annotated[TimeService, Depends(get_service)]

router = APIRouter(
    prefix="/times",
    tags=["الأوقات"],
    dependencies=[Depends(get_current_user)],
)


def _full_schedule(payload: TimeCreateRequest) -> DaySchedule:
    return {day: value.to_range() if (value := getattr(payload, day)) else None for day in WEEKDAYS}


def _partial_schedule(payload: TimeUpdateRequest) -> DaySchedule:
    changes: DaySchedule = {}
    for day in WEEKDAYS:
        if day in payload.model_fields_set:
            value = getattr(payload, day)
            changes[day] = value.to_range() if value else None
    return changes


@router.post(
    "",
    response_model=TimeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء وقت",
)
async def create(
    payload: TimeCreateRequest, service: ServiceDep, _: CurrentSuperAdmin
) -> TimeResponse:
    time = await service.create(CreateTimeInput(name=payload.name, days=_full_schedule(payload)))
    return TimeResponse.from_entity(time)


@router.get("", response_model=TimeListResponse, summary="قائمة الأوقات")
async def list_(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TimeListResponse:
    items, total = await service.list(Page(limit=limit, offset=offset))
    return TimeListResponse(
        items=[TimeResponse.from_entity(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{time_id}", response_model=TimeResponse, summary="عرض وقت")
async def get(time_id: UUID, service: ServiceDep) -> TimeResponse:
    return TimeResponse.from_entity(await service.get(time_id))


@router.patch("/{time_id}", response_model=TimeResponse, summary="تعديل وقت")
async def update(
    time_id: UUID, payload: TimeUpdateRequest, service: ServiceDep, _: CurrentSuperAdmin
) -> TimeResponse:
    name = payload.name if payload.name is not None else UNSET
    time = await service.update(
        time_id, UpdateTimeInput(name=name, days=_partial_schedule(payload))
    )
    return TimeResponse.from_entity(time)


@router.delete(
    "/{time_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف وقت",
)
async def delete(time_id: UUID, service: ServiceDep, _: CurrentSuperAdmin) -> None:
    await service.delete(time_id)
