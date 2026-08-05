"""Upcoming exams presentation layer.

Teachers plan exams for students in their own halaqahs; the administration sees
and edits every plan.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status

from institute_administration.api.dependencies import DbSession
from institute_administration.api.scoping import ScopeDep
from institute_administration.modules.identity.dependencies import (
    get_current_user,
    require_roles,
)
from institute_administration.modules.identity.domain import User, UserRole
from institute_administration.modules.students.repository import SqlAlchemyStudentRepository
from institute_administration.modules.upcoming_exams.domain import (
    ExamStatus,
    UpcomingExamNotFoundError,
    validate_parameters,
)
from institute_administration.modules.upcoming_exams.repository import (
    SqlAlchemyUpcomingExamRepository,
)
from institute_administration.modules.upcoming_exams.schemas import (
    NextExamItem,
    NextExamsResponse,
    UpcomingExamCreateRequest,
    UpcomingExamListResponse,
    UpcomingExamResponse,
    UpcomingExamUpdateRequest,
)
from institute_administration.shared.application.exceptions import AuthorizationError
from institute_administration.shared.application.pagination import Page


def get_repository(session: DbSession) -> SqlAlchemyUpcomingExamRepository:
    return SqlAlchemyUpcomingExamRepository(session)


RepositoryDep = Annotated[SqlAlchemyUpcomingExamRepository, Depends(get_repository)]
CurrentWriter = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.TEACHER))]

router = APIRouter(
    prefix="/upcoming-exams",
    tags=["الاختبارات القادمة"],
    dependencies=[Depends(get_current_user)],
)

_FORBIDDEN = "ليس لديك صلاحية على هذه الحلقة"


@router.post(
    "",
    response_model=UpcomingExamResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="جدولة اختبار قادم",
)
async def create(
    payload: UpcomingExamCreateRequest,
    repository: RepositoryDep,
    scope: ScopeDep,
    session: DbSession,
    _: CurrentWriter,
) -> UpcomingExamResponse:
    teacher_id = payload.teacher_id
    if not scope.is_admin:
        if not scope.allows_halaqah(payload.halaqah_id):
            raise AuthorizationError(_FORBIDDEN)
        assert scope.teacher_id is not None
        teacher_id = scope.teacher_id
    if teacher_id is None:
        raise AuthorizationError("يجب تحديد المعلم")

    student = await SqlAlchemyStudentRepository(session).get_by_id(payload.student_id)
    if student is None or student.halaqah_id != payload.halaqah_id:
        raise AuthorizationError("الطالب لا ينتمي إلى هذه الحلقة")

    validate_parameters(payload.part, payload.exam_from, payload.exam_to)
    exam_id = await repository.add(
        student_id=payload.student_id,
        teacher_id=teacher_id,
        halaqah_id=payload.halaqah_id,
        scheduled_date=payload.scheduled_date,
        part=payload.part,
        exam_from=payload.exam_from,
        exam_to=payload.exam_to,
        notes=payload.notes,
    )
    view = await repository.get_view(exam_id)
    if view is None:  # pragma: no cover - just written
        raise UpcomingExamNotFoundError
    return UpcomingExamResponse.from_view(view)


@router.get("", response_model=UpcomingExamListResponse, summary="قائمة الاختبارات القادمة")
async def list_(
    repository: RepositoryDep,
    scope: ScopeDep,
    student_id: Annotated[UUID | None, Query(description="تصفية حسب الطالب")] = None,
    halaqah_id: Annotated[UUID | None, Query(description="تصفية حسب الحلقة")] = None,
    status: Annotated[ExamStatus | None, Query(description="تصفية حسب الحالة")] = None,
    date_from: Annotated[date | None, Query(description="من تاريخ (شامل)")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UpcomingExamListResponse:
    restrict = None if scope.is_admin else scope.halaqah_ids
    if restrict is not None and not restrict:
        return UpcomingExamListResponse(items=[], total=0, limit=limit, offset=offset)

    items = await repository.list_views(
        Page(limit=limit, offset=offset),
        student_id=student_id,
        halaqah_id=halaqah_id,
        status=status,
        date_from=date_from,
        halaqah_ids=restrict,
    )
    total = await repository.count(
        student_id=student_id,
        halaqah_id=halaqah_id,
        status=status,
        date_from=date_from,
        halaqah_ids=restrict,
    )
    return UpcomingExamListResponse(
        items=[UpcomingExamResponse.from_view(v) for v in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/next",
    response_model=NextExamsResponse,
    summary="الاختبار القادم لكل طالب",
)
async def next_exams(
    repository: RepositoryDep,
    scope: ScopeDep,
    session: DbSession,
    student_ids: Annotated[
        list[UUID], Query(description="معرّفات الطلاب", min_length=1, max_length=200)
    ],
    on_or_after: Annotated[date | None, Query(description="اعتباراً من (افتراضيًا اليوم)")] = None,
) -> NextExamsResponse:
    # Authorise by the student's *current* halaqah, like «آخر تسميع» does.
    if not scope.is_admin:
        students = SqlAlchemyStudentRepository(session)
        student_ids = [
            sid
            for sid in student_ids
            if (student := await students.get_by_id(sid)) is not None
            and scope.allows_halaqah(student.halaqah_id)
        ]
        if not student_ids:
            return NextExamsResponse(items=[])

    by_student = await repository.next_per_student(
        student_ids, on_or_after=on_or_after or date.today()
    )
    return NextExamsResponse(
        items=[
            NextExamItem(
                student_id=sid,
                exam=(
                    UpcomingExamResponse.from_view(by_student[sid]) if sid in by_student else None
                ),
            )
            for sid in student_ids
        ]
    )


@router.patch("/{exam_id}", response_model=UpcomingExamResponse, summary="تعديل اختبار قادم")
async def update(
    exam_id: UUID,
    payload: UpcomingExamUpdateRequest,
    repository: RepositoryDep,
    scope: ScopeDep,
    _: CurrentWriter,
) -> UpcomingExamResponse:
    existing = await repository.get_view(exam_id)
    if existing is None or not scope.allows_halaqah(existing.halaqah_id):
        raise UpcomingExamNotFoundError
    validate_parameters(
        payload.part if payload.part is not None else existing.part,
        payload.exam_from if payload.exam_from is not None else existing.exam_from,
        payload.exam_to if payload.exam_to is not None else existing.exam_to,
    )
    await repository.update(
        exam_id,
        scheduled_date=payload.scheduled_date,
        part=payload.part,
        exam_from=payload.exam_from,
        exam_to=payload.exam_to,
        notes=payload.notes,
        status=payload.status,
        clear=frozenset(payload.clear),
    )
    view = await repository.get_view(exam_id)
    if view is None:  # pragma: no cover - just updated
        raise UpcomingExamNotFoundError
    return UpcomingExamResponse.from_view(view)


@router.delete("/{exam_id}", status_code=http_status.HTTP_204_NO_CONTENT, summary="حذف اختبار قادم")
async def delete(
    exam_id: UUID, repository: RepositoryDep, scope: ScopeDep, _: CurrentWriter
) -> None:
    existing = await repository.get_view(exam_id)
    if existing is None or not scope.allows_halaqah(existing.halaqah_id):
        raise UpcomingExamNotFoundError
    await repository.delete(exam_id)
