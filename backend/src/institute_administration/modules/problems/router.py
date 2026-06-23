"""Problems presentation layer: CRUD for problem levels and problems."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from institute_administration.api.dependencies import DbSession
from institute_administration.modules.identity.dependencies import (
    CurrentSuperAdmin,
    get_current_user,
)
from institute_administration.modules.problems.domain import (
    ProblemLevelRepository,
    ProblemRepository,
)
from institute_administration.modules.problems.repository import (
    SqlAlchemyProblemLevelRepository,
    SqlAlchemyProblemRepository,
)
from institute_administration.modules.problems.schemas import (
    ProblemCreateRequest,
    ProblemLevelCreateRequest,
    ProblemLevelListResponse,
    ProblemLevelResponse,
    ProblemLevelUpdateRequest,
    ProblemListResponse,
    ProblemResponse,
    ProblemUpdateRequest,
)
from institute_administration.modules.problems.service import (
    CreateProblemInput,
    CreateProblemLevelInput,
    ProblemLevelService,
    ProblemService,
    UpdateProblemInput,
    UpdateProblemLevelInput,
)
from institute_administration.shared.application.pagination import Page


def _level_repo(session: DbSession) -> ProblemLevelRepository:
    return SqlAlchemyProblemLevelRepository(session)


def _problem_repo(session: DbSession) -> ProblemRepository:
    return SqlAlchemyProblemRepository(session)


def _level_service(session: DbSession) -> ProblemLevelService:
    return ProblemLevelService(
        SqlAlchemyProblemLevelRepository(session),
        SqlAlchemyProblemRepository(session),
    )


def _problem_service(session: DbSession) -> ProblemService:
    return ProblemService(
        SqlAlchemyProblemRepository(session),
        SqlAlchemyProblemLevelRepository(session),
    )


LevelServiceDep = Annotated[ProblemLevelService, Depends(_level_service)]
ProblemServiceDep = Annotated[ProblemService, Depends(_problem_service)]

router = APIRouter(
    tags=["الصعوبات"],
    dependencies=[Depends(get_current_user)],
)

# ---------------------------------------------------------------------------
# Problem Levels  /problem-levels
# ---------------------------------------------------------------------------


@router.post(
    "/problem-levels",
    response_model=ProblemLevelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء مستوى صعوبة",
)
async def create_level(
    payload: ProblemLevelCreateRequest,
    service: LevelServiceDep,
    _: CurrentSuperAdmin,
) -> ProblemLevelResponse:
    level = await service.create(CreateProblemLevelInput(name=payload.name))
    return ProblemLevelResponse.from_entity(level)


@router.get(
    "/problem-levels",
    response_model=ProblemLevelListResponse,
    summary="قائمة مستويات الصعوبة",
)
async def list_levels(
    service: LevelServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProblemLevelListResponse:
    items, total = await service.list(Page(limit=limit, offset=offset))
    return ProblemLevelListResponse(
        items=[ProblemLevelResponse.from_entity(lvl) for lvl in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/problem-levels/{level_id}",
    response_model=ProblemLevelResponse,
    summary="عرض مستوى صعوبة",
)
async def get_level(level_id: UUID, service: LevelServiceDep) -> ProblemLevelResponse:
    return ProblemLevelResponse.from_entity(await service.get(level_id))


@router.patch(
    "/problem-levels/{level_id}",
    response_model=ProblemLevelResponse,
    summary="تعديل مستوى صعوبة",
)
async def update_level(
    level_id: UUID,
    payload: ProblemLevelUpdateRequest,
    service: LevelServiceDep,
    _: CurrentSuperAdmin,
) -> ProblemLevelResponse:
    data = payload.model_dump(exclude_unset=True)
    level = await service.update(level_id, UpdateProblemLevelInput(**data))
    return ProblemLevelResponse.from_entity(level)


@router.delete(
    "/problem-levels/{level_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف مستوى صعوبة",
)
async def delete_level(
    level_id: UUID, service: LevelServiceDep, _: CurrentSuperAdmin
) -> None:
    await service.delete(level_id)


# ---------------------------------------------------------------------------
# Problems  /problems
# ---------------------------------------------------------------------------


@router.post(
    "/problems",
    response_model=ProblemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء صعوبة",
)
async def create_problem(
    payload: ProblemCreateRequest,
    service: ProblemServiceDep,
    _: CurrentSuperAdmin,
) -> ProblemResponse:
    problem = await service.create(
        CreateProblemInput(name=payload.name, level_id=payload.level_id)
    )
    return ProblemResponse.from_entity(problem)


@router.get(
    "/problems",
    response_model=ProblemListResponse,
    summary="قائمة الصعوبات",
)
async def list_problems(
    service: ProblemServiceDep,
    level_id: Annotated[UUID | None, Query(description="تصفية حسب المستوى")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProblemListResponse:
    items, total = await service.list(Page(limit=limit, offset=offset), level_id=level_id)
    return ProblemListResponse(
        items=[ProblemResponse.from_entity(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/problems/{problem_id}",
    response_model=ProblemResponse,
    summary="عرض صعوبة",
)
async def get_problem(problem_id: UUID, service: ProblemServiceDep) -> ProblemResponse:
    return ProblemResponse.from_entity(await service.get(problem_id))


@router.patch(
    "/problems/{problem_id}",
    response_model=ProblemResponse,
    summary="تعديل صعوبة",
)
async def update_problem(
    problem_id: UUID,
    payload: ProblemUpdateRequest,
    service: ProblemServiceDep,
    _: CurrentSuperAdmin,
) -> ProblemResponse:
    data = payload.model_dump(exclude_unset=True)
    problem = await service.update(problem_id, UpdateProblemInput(**data))
    return ProblemResponse.from_entity(problem)


@router.delete(
    "/problems/{problem_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف صعوبة",
)
async def delete_problem(
    problem_id: UUID, service: ProblemServiceDep, _: CurrentSuperAdmin
) -> None:
    await service.delete(problem_id)
