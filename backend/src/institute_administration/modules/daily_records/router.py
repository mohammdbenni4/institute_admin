"""Daily records presentation layer: CRUD + bulk attendance.

Reads are restricted to the caller's own halaqahs (super admins see all);
writes are restricted to teachers and super admins. Card scores are computed
with the institute's configured scoring policy.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from institute_administration.api.dependencies import DbSession
from institute_administration.api.scoping import ScopeDep
from institute_administration.modules.daily_records.domain import (
    DailyRecord,
    DailyRecordNotFoundError,
)
from institute_administration.modules.daily_records.repository import (
    SqlAlchemyDailyRecordRepository,
)
from institute_administration.modules.daily_records.schemas import (
    BulkAttendanceRequest,
    BulkAttendanceResponse,
    BulkUpsertRequest,
    BulkUpsertResponse,
    DailyRecordCreateRequest,
    DailyRecordListResponse,
    DailyRecordResponse,
    DailyRecordUpdateRequest,
    LatestRecitationItem,
    LatestRecitationsResponse,
)
from institute_administration.modules.daily_records.service import (
    BulkAttendanceEntry,
    CreateDailyRecordInput,
    DailyRecordService,
    UpdateDailyRecordInput,
    UpsertDailyRecordEntry,
)
from institute_administration.modules.identity.dependencies import (
    get_current_user,
    require_roles,
)
from institute_administration.modules.identity.domain import User, UserRole
from institute_administration.modules.problems.repository import SqlAlchemyProblemRepository
from institute_administration.modules.scoring.repository import (
    SqlAlchemyScoringSettingsRepository,
    StudentScoringPolicyResolver,
)
from institute_administration.modules.students.repository import SqlAlchemyStudentRepository
from institute_administration.shared.application.exceptions import AuthorizationError
from institute_administration.shared.application.pagination import Page


async def get_service(session: DbSession) -> DailyRecordService:
    """Build the service with a per-student policy resolver.

    `policy` stays the institute-wide fallback (and keeps the service usable
    without a database); the resolver overrides it for students pinned to a
    named scoring preset.
    """
    policy = await SqlAlchemyScoringSettingsRepository(session).get_policy()
    resolver = StudentScoringPolicyResolver(session)
    return DailyRecordService(SqlAlchemyDailyRecordRepository(session), policy, resolver)


ServiceDep = Annotated[DailyRecordService, Depends(get_service)]


async def _to_response(record: DailyRecord, session: DbSession) -> DailyRecordResponse:
    problems = await SqlAlchemyProblemRepository(session).get_by_ids(record.problem_ids)
    return DailyRecordResponse.from_entity(record, problems)


async def _to_list_response(
    records: list[DailyRecord],
    session: DbSession,
    total: int,
    limit: int,
    offset: int,
) -> DailyRecordListResponse:
    all_ids = list({pid for r in records for pid in r.problem_ids})
    by_id = {}
    if all_ids:
        for p in await SqlAlchemyProblemRepository(session).get_by_ids(all_ids):
            by_id[p.id] = p
    return DailyRecordListResponse(
        items=[
            DailyRecordResponse.from_entity(
                r, [by_id[pid] for pid in r.problem_ids if pid in by_id]
            )
            for r in records
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


# Writes are allowed for teachers and super admins.
CurrentWriter = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.TEACHER))]

router = APIRouter(
    prefix="/daily-records",
    tags=["السجلات اليومية"],
    dependencies=[Depends(get_current_user)],
)

_FORBIDDEN = "ليس لديك صلاحية على هذه الحلقة"


@router.post(
    "",
    response_model=DailyRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء سجل يومي",
)
async def create(
    payload: DailyRecordCreateRequest,
    service: ServiceDep,
    scope: ScopeDep,
    session: DbSession,
    _: CurrentWriter,
) -> DailyRecordResponse:
    data = payload.model_dump()
    if not scope.is_admin:
        if not scope.allows_halaqah(payload.halaqah_id):
            raise AuthorizationError(_FORBIDDEN)
        data["teacher_id"] = scope.teacher_id  # a teacher records only as themselves
    record = await service.create(CreateDailyRecordInput(**data))
    return await _to_response(record, session)


@router.post(
    "/bulk-attendance",
    response_model=BulkAttendanceResponse,
    summary="تسجيل حضور جماعي للحلقة",
)
async def bulk_attendance(
    payload: BulkAttendanceRequest, service: ServiceDep, scope: ScopeDep, _: CurrentWriter
) -> BulkAttendanceResponse:
    teacher_id = payload.teacher_id
    if not scope.is_admin:
        if not scope.allows_halaqah(payload.halaqah_id):
            raise AuthorizationError(_FORBIDDEN)
        assert scope.teacher_id is not None
        teacher_id = scope.teacher_id
    record_date = payload.record_date or date.today()
    created, updated = await service.set_attendance(
        halaqah_id=payload.halaqah_id,
        teacher_id=teacher_id,
        record_date=record_date,
        entries=[
            BulkAttendanceEntry(e.student_id, e.present, e.excused, e.late, e.excuse_reason)
            for e in payload.entries
        ],
    )
    return BulkAttendanceResponse(record_date=record_date, created=created, updated=updated)


@router.post(
    "/bulk-upsert",
    response_model=BulkUpsertResponse,
    summary="رفع دفعة سجلات (إنشاء أو تحديث حسب الطالب والتاريخ)",
)
async def bulk_upsert(
    payload: BulkUpsertRequest,
    service: ServiceDep,
    scope: ScopeDep,
    session: DbSession,
    _: CurrentWriter,
) -> BulkUpsertResponse:
    teacher_id = payload.teacher_id
    if not scope.is_admin:
        if not scope.allows_halaqah(payload.halaqah_id):
            raise AuthorizationError(_FORBIDDEN)
        assert scope.teacher_id is not None
        teacher_id = scope.teacher_id
    records, created, updated = await service.bulk_upsert(
        halaqah_id=payload.halaqah_id,
        teacher_id=teacher_id,
        entries=[UpsertDailyRecordEntry(**item.model_dump()) for item in payload.records],
    )
    listed = await _to_list_response(records, session, len(records), len(records), 0)
    return BulkUpsertResponse(items=listed.items, created=created, updated=updated)


@router.get(
    "/latest-recitations",
    response_model=LatestRecitationsResponse,
    summary="آخر تسميع وآخر واجب لكل طالب",
)
async def latest_recitations(
    service: ServiceDep,
    scope: ScopeDep,
    session: DbSession,
    student_ids: Annotated[
        list[UUID], Query(description="معرّفات الطلاب", min_length=1, max_length=200)
    ],
    before: Annotated[
        date | None, Query(description="آخر تسميع قبل هذا التاريخ (غير شامل)")
    ] = None,
) -> LatestRecitationsResponse:
    # Authorise by *student*, not by the halaqah stored on the old record: a student
    # who moved between halaqahs would otherwise lose their whole exam history to
    # their new teacher, showing «لم يُسجّل تسميع بعد» forever.
    if not scope.is_admin:
        students = SqlAlchemyStudentRepository(session)
        allowed = {
            sid
            for sid in student_ids
            if (student := await students.get_by_id(sid)) is not None
            and scope.allows_halaqah(student.halaqah_id)
        }
        student_ids = [sid for sid in student_ids if sid in allowed]
        if not student_ids:
            return LatestRecitationsResponse(items=[])

    recitations, homework = await service.latest_recitations(student_ids, before=before)

    resolved = await _to_list_response(
        list(recitations.values()), session, len(recitations), max(len(recitations), 1), 0
    )
    by_student = {item.student_id: item for item in resolved.items}
    return LatestRecitationsResponse(
        items=[
            LatestRecitationItem(
                student_id=sid,
                last_recitation=by_student.get(sid),
                homework=homework.get(sid),
            )
            for sid in student_ids
        ]
    )


@router.get("", response_model=DailyRecordListResponse, summary="قائمة السجلات اليومية")
async def list_(
    service: ServiceDep,
    scope: ScopeDep,
    session: DbSession,
    student_id: Annotated[UUID | None, Query(description="تصفية حسب الطالب")] = None,
    teacher_id: Annotated[UUID | None, Query(description="تصفية حسب المعلم")] = None,
    halaqah_id: Annotated[UUID | None, Query(description="تصفية حسب الحلقة")] = None,
    record_date: Annotated[date | None, Query(description="تصفية حسب تاريخ السجل")] = None,
    date_from: Annotated[date | None, Query(description="من تاريخ (شامل)")] = None,
    date_to: Annotated[date | None, Query(description="إلى تاريخ (شامل)")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DailyRecordListResponse:
    empty = DailyRecordListResponse(items=[], total=0, limit=limit, offset=offset)
    restrict: frozenset[UUID] | None = None
    if not scope.is_admin:
        if not scope.halaqah_ids:
            return empty
        if halaqah_id is not None and not scope.allows_halaqah(halaqah_id):
            return empty
        restrict = scope.halaqah_ids
    items, total = await service.list(
        Page(limit=limit, offset=offset),
        student_id=student_id,
        teacher_id=teacher_id,
        halaqah_id=halaqah_id,
        halaqah_ids=restrict,
        record_date=record_date,
        date_from=date_from,
        date_to=date_to,
    )
    return await _to_list_response(items, session, total, limit, offset)


@router.get("/{record_id}", response_model=DailyRecordResponse, summary="عرض سجل يومي")
async def get(
    record_id: UUID, service: ServiceDep, scope: ScopeDep, session: DbSession
) -> DailyRecordResponse:
    record = await service.get(record_id)
    if not scope.allows_halaqah(record.halaqah_id):
        raise DailyRecordNotFoundError
    return await _to_response(record, session)


@router.patch("/{record_id}", response_model=DailyRecordResponse, summary="تعديل سجل يومي")
async def update(
    record_id: UUID,
    payload: DailyRecordUpdateRequest,
    service: ServiceDep,
    scope: ScopeDep,
    session: DbSession,
    _: CurrentWriter,
) -> DailyRecordResponse:
    existing = await service.get(record_id)
    if not scope.allows_halaqah(existing.halaqah_id):
        raise DailyRecordNotFoundError
    data = payload.model_dump(exclude_unset=True)
    if not scope.is_admin and "halaqah_id" in data and not scope.allows_halaqah(data["halaqah_id"]):
        raise AuthorizationError(_FORBIDDEN)
    record = await service.update(record_id, UpdateDailyRecordInput(**data))
    return await _to_response(record, session)


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف سجل يومي",
)
async def delete(record_id: UUID, service: ServiceDep, scope: ScopeDep, _: CurrentWriter) -> None:
    existing = await service.get(record_id)
    if not scope.allows_halaqah(existing.halaqah_id):
        raise DailyRecordNotFoundError
    await service.delete(record_id)
