"""Scoring settings presentation layer.

Reading is open to any authenticated user (the teacher app uses it to preview
the live total); updating is restricted to super admins.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from institute_administration.api.dependencies import DbSession
from institute_administration.modules.identity.dependencies import (
    CurrentSuperAdmin,
    get_current_user,
)
from institute_administration.modules.scoring.repository import (
    SqlAlchemyScoringPresetRepository,
    SqlAlchemyScoringSettingsRepository,
)
from institute_administration.modules.scoring.schemas import (
    ScoringPresetListResponse,
    ScoringPresetResponse,
    ScoringPresetWriteRequest,
    ScoringSettingsResponse,
    ScoringSettingsUpdate,
)


def get_repository(session: DbSession) -> SqlAlchemyScoringSettingsRepository:
    return SqlAlchemyScoringSettingsRepository(session)


RepositoryDep = Annotated[SqlAlchemyScoringSettingsRepository, Depends(get_repository)]

router = APIRouter(
    prefix="/scoring-settings",
    tags=["إعدادات النقاط"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=ScoringSettingsResponse, summary="عرض إعدادات النقاط")
async def get(repository: RepositoryDep) -> ScoringSettingsResponse:
    return ScoringSettingsResponse.model_validate(await repository.get())


@router.put("", response_model=ScoringSettingsResponse, summary="تعديل إعدادات النقاط")
async def update(
    payload: ScoringSettingsUpdate, repository: RepositoryDep, _: CurrentSuperAdmin
) -> ScoringSettingsResponse:
    return ScoringSettingsResponse.model_validate(await repository.upsert(payload.to_settings()))


# --- Named presets ----------------------------------------------------------------


def get_preset_repository(session: DbSession) -> SqlAlchemyScoringPresetRepository:
    return SqlAlchemyScoringPresetRepository(session)


PresetRepositoryDep = Annotated[SqlAlchemyScoringPresetRepository, Depends(get_preset_repository)]

presets_router = APIRouter(
    prefix="/scoring-presets",
    tags=["أنظمة تسعير النقاط"],
    dependencies=[Depends(get_current_user)],
)


@presets_router.get("", response_model=ScoringPresetListResponse, summary="قائمة أنظمة التسعير")
async def list_presets(repository: PresetRepositoryDep) -> ScoringPresetListResponse:
    """Readable by any authenticated user: the teacher app lists these to assign one
    to a student, and to price the live total it previews while a record is edited."""
    presets = await repository.list()
    items = [ScoringPresetResponse.from_entity(p) for p in presets]
    return ScoringPresetListResponse(items=items, total=len(items))


@presets_router.post(
    "",
    response_model=ScoringPresetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء نظام تسعير",
)
async def create_preset(
    payload: ScoringPresetWriteRequest, repository: PresetRepositoryDep, _: CurrentSuperAdmin
) -> ScoringPresetResponse:
    preset = await repository.create(payload.name, payload.to_settings())
    return ScoringPresetResponse.from_entity(preset)


@presets_router.get("/{preset_id}", response_model=ScoringPresetResponse, summary="عرض نظام تسعير")
async def get_preset(preset_id: UUID, repository: PresetRepositoryDep) -> ScoringPresetResponse:
    return ScoringPresetResponse.from_entity(await repository.get(preset_id))


@presets_router.put(
    "/{preset_id}", response_model=ScoringPresetResponse, summary="تعديل نظام تسعير"
)
async def update_preset(
    preset_id: UUID,
    payload: ScoringPresetWriteRequest,
    repository: PresetRepositoryDep,
    _: CurrentSuperAdmin,
) -> ScoringPresetResponse:
    preset = await repository.update(preset_id, name=payload.name, settings=payload.to_settings())
    return ScoringPresetResponse.from_entity(preset)


@presets_router.delete(
    "/{preset_id}", status_code=status.HTTP_204_NO_CONTENT, summary="حذف نظام تسعير"
)
async def delete_preset(
    preset_id: UUID, repository: PresetRepositoryDep, _: CurrentSuperAdmin
) -> None:
    """Students pinned to this preset fall back to the institute-wide settings
    (``students.scoring_preset_id`` is ``ON DELETE SET NULL``)."""
    await repository.delete(preset_id)
