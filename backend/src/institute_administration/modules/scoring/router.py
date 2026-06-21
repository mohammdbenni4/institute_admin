"""Scoring settings presentation layer.

Reading is open to any authenticated user (the teacher app uses it to preview
the live total); updating is restricted to super admins.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from institute_administration.api.dependencies import DbSession
from institute_administration.modules.identity.dependencies import (
    CurrentSuperAdmin,
    get_current_user,
)
from institute_administration.modules.scoring.repository import SqlAlchemyScoringSettingsRepository
from institute_administration.modules.scoring.schemas import (
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
