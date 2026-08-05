"""Parent summons presentation layer.

A teacher raises a request for one of their own students and can watch its
status; only the administration may move it forward or reply.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status

from institute_administration.api.dependencies import DbSession
from institute_administration.api.scoping import ScopeDep
from institute_administration.modules.identity.dependencies import (
    CurrentSuperAdmin,
    get_current_user,
    require_roles,
)
from institute_administration.modules.identity.domain import User, UserRole
from institute_administration.modules.parent_summons.domain import (
    ParentSummonNotFoundError,
    SummonStatus,
)
from institute_administration.modules.parent_summons.repository import (
    SqlAlchemyParentSummonRepository,
)
from institute_administration.modules.parent_summons.schemas import (
    ParentSummonCreateRequest,
    ParentSummonListResponse,
    ParentSummonResponse,
    ParentSummonUpdateRequest,
)
from institute_administration.modules.students.repository import SqlAlchemyStudentRepository
from institute_administration.shared.application.exceptions import AuthorizationError
from institute_administration.shared.application.pagination import Page


def get_repository(session: DbSession) -> SqlAlchemyParentSummonRepository:
    return SqlAlchemyParentSummonRepository(session)


RepositoryDep = Annotated[SqlAlchemyParentSummonRepository, Depends(get_repository)]
CurrentWriter = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.TEACHER))]

router = APIRouter(
    prefix="/parent-summons",
    tags=["استدعاء ولي الأمر"],
    dependencies=[Depends(get_current_user)],
)

_FORBIDDEN = "ليس لديك صلاحية على هذه الحلقة"


@router.post(
    "",
    response_model=ParentSummonResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="طلب استدعاء ولي أمر",
)
async def create(
    payload: ParentSummonCreateRequest,
    repository: RepositoryDep,
    scope: ScopeDep,
    session: DbSession,
    _: CurrentWriter,
) -> ParentSummonResponse:
    teacher_id = payload.teacher_id
    if not scope.is_admin:
        if not scope.allows_halaqah(payload.halaqah_id):
            raise AuthorizationError(_FORBIDDEN)
        assert scope.teacher_id is not None
        teacher_id = scope.teacher_id  # a teacher requests only as themselves
    if teacher_id is None:
        raise AuthorizationError("يجب تحديد المعلم")

    # The student must really belong to the halaqah the request is filed under.
    student = await SqlAlchemyStudentRepository(session).get_by_id(payload.student_id)
    if student is None or student.halaqah_id != payload.halaqah_id:
        raise AuthorizationError("الطالب لا ينتمي إلى هذه الحلقة")

    summon_id = await repository.add(
        student_id=payload.student_id,
        teacher_id=teacher_id,
        halaqah_id=payload.halaqah_id,
        reason=payload.reason.strip(),
    )
    view = await repository.get_view(summon_id)
    if view is None:  # pragma: no cover - just written
        raise ParentSummonNotFoundError
    return ParentSummonResponse.from_view(view)


@router.get("", response_model=ParentSummonListResponse, summary="قائمة طلبات الاستدعاء")
async def list_(
    repository: RepositoryDep,
    scope: ScopeDep,
    status: Annotated[SummonStatus | None, Query(description="تصفية حسب الحالة")] = None,
    student_id: Annotated[UUID | None, Query(description="تصفية حسب الطالب")] = None,
    teacher_id: Annotated[UUID | None, Query(description="تصفية حسب المعلم")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ParentSummonListResponse:
    # A teacher sees only requests filed for their own halaqahs.
    restrict = None if scope.is_admin else scope.halaqah_ids
    if restrict is not None and not restrict:
        return ParentSummonListResponse(
            items=[], total=0, limit=limit, offset=offset, counts=dict.fromkeys(SummonStatus, 0)
        )

    items = await repository.list_views(
        Page(limit=limit, offset=offset),
        status=status,
        student_id=student_id,
        teacher_id=teacher_id,
        halaqah_ids=restrict,
    )
    total = await repository.count(
        status=status, student_id=student_id, teacher_id=teacher_id, halaqah_ids=restrict
    )
    counts = await repository.count_by_status(halaqah_ids=restrict)
    return ParentSummonListResponse(
        items=[ParentSummonResponse.from_view(v) for v in items],
        total=total,
        limit=limit,
        offset=offset,
        counts=counts,
    )


@router.get("/{summon_id}", response_model=ParentSummonResponse, summary="عرض طلب استدعاء")
async def get(summon_id: UUID, repository: RepositoryDep, scope: ScopeDep) -> ParentSummonResponse:
    view = await repository.get_view(summon_id)
    if view is None or not scope.allows_halaqah(view.halaqah_id):
        raise ParentSummonNotFoundError
    return ParentSummonResponse.from_view(view)


@router.patch(
    "/{summon_id}",
    response_model=ParentSummonResponse,
    summary="تحديث حالة الطلب والرد على المعلم",
)
async def update(
    summon_id: UUID,
    payload: ParentSummonUpdateRequest,
    repository: RepositoryDep,
    _: CurrentSuperAdmin,
) -> ParentSummonResponse:
    existing = await repository.get_view(summon_id)
    if existing is None:
        raise ParentSummonNotFoundError
    await repository.update(summon_id, status=payload.status, admin_response=payload.admin_response)
    view = await repository.get_view(summon_id)
    if view is None:  # pragma: no cover - just updated
        raise ParentSummonNotFoundError
    return ParentSummonResponse.from_view(view)


@router.delete(
    "/{summon_id}", status_code=http_status.HTTP_204_NO_CONTENT, summary="حذف طلب استدعاء"
)
async def delete(summon_id: UUID, repository: RepositoryDep, _: CurrentSuperAdmin) -> None:
    if await repository.get_view(summon_id) is None:
        raise ParentSummonNotFoundError
    await repository.delete(summon_id)
