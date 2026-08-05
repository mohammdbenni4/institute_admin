"""Institute settings presentation layer.

Reading is open to any authenticated user (the printed report needs the institute's
name and logo); updating is restricted to super admins.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from institute_administration.api.dependencies import DbSession
from institute_administration.modules.identity.dependencies import (
    CurrentSuperAdmin,
    get_current_user,
)
from institute_administration.modules.institute.repository import (
    SqlAlchemyInstituteSettingsRepository,
)
from institute_administration.modules.institute.schemas import (
    InstituteSettingsResponse,
    InstituteSettingsUpdate,
)


def get_repository(session: DbSession) -> SqlAlchemyInstituteSettingsRepository:
    return SqlAlchemyInstituteSettingsRepository(session)


RepositoryDep = Annotated[SqlAlchemyInstituteSettingsRepository, Depends(get_repository)]

router = APIRouter(
    prefix="/institute-settings",
    tags=["إعدادات المعهد"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=InstituteSettingsResponse, summary="عرض بيانات المعهد")
async def get(repository: RepositoryDep) -> InstituteSettingsResponse:
    return InstituteSettingsResponse.model_validate(await repository.get())


@router.put("", response_model=InstituteSettingsResponse, summary="تعديل بيانات المعهد")
async def update(
    payload: InstituteSettingsUpdate, repository: RepositoryDep, _: CurrentSuperAdmin
) -> InstituteSettingsResponse:
    return InstituteSettingsResponse.model_validate(await repository.upsert(payload.to_settings()))
