"""Analytics presentation layer: read-only reporting endpoints.

Open to any authenticated user; the admin dashboard is the primary consumer.
When the date window is omitted it defaults to the current calendar month.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from institute_administration.api.dependencies import DbSession
from institute_administration.api.scoping import ScopeDep
from institute_administration.core.config import get_settings
from institute_administration.modules.analytics.repository import SqlAlchemyAnalyticsRepository
from institute_administration.modules.analytics.schemas import (
    AtRiskResponse,
    AtRiskStudentResponse,
    AttendanceMatrixResponse,
    HalaqahLeaderboardResponse,
    LeaderboardResponse,
    OverviewResponse,
)
from institute_administration.modules.analytics.service import AnalyticsService
from institute_administration.modules.identity.dependencies import get_current_user


def get_service(session: DbSession) -> AnalyticsService:
    return AnalyticsService(SqlAlchemyAnalyticsRepository(session))


ServiceDep = Annotated[AnalyticsService, Depends(get_service)]

router = APIRouter(
    prefix="/analytics",
    tags=["التحليلات"],
    dependencies=[Depends(get_current_user)],
)

DateFrom = Annotated[date | None, Query(description="من تاريخ (افتراضيًا بداية الشهر الحالي)")]
DateTo = Annotated[date | None, Query(description="إلى تاريخ (افتراضيًا اليوم)")]


def _resolve(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    today = date.today()
    return (date_from or today.replace(day=1), date_to or today)


@router.get(
    "/attendance-matrix",
    response_model=AttendanceMatrixResponse,
    summary="كشف الحضور الشهري (مُجمَّع ومُقسَّم إلى صفحات)",
)
async def attendance_matrix(
    service: ServiceDep,
    scope: ScopeDep,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    halaqah_id: Annotated[UUID | None, Query(description="تصفية حسب الحلقة")] = None,
    teacher_id: Annotated[UUID | None, Query(description="تصفية حسب المعلم")] = None,
    search: Annotated[str | None, Query(description="بحث باسم الطالب")] = None,
    status: Annotated[
        Literal["present", "late", "absent", "excused"] | None,
        Query(description="إبقاء الطلاب الذين سُجِّلت لهم هذه الحالة"),
    ] = None,
    on_day: Annotated[date | None, Query(description="حصر العدادات في يوم واحد")] = None,
    sort: Annotated[
        Literal["halaqah", "name", "rate-asc", "rate-desc"], Query(description="الترتيب")
    ] = "halaqah",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AttendanceMatrixResponse:
    """One aggregated row per student instead of every daily record in the month."""
    start, end = _resolve(date_from, date_to)
    matrix = await service.attendance_matrix(
        start,
        end,
        limit=limit,
        offset=offset,
        halaqah_id=halaqah_id,
        teacher_id=teacher_id,
        search=search,
        status=status,
        on_day=on_day,
        sort=sort,
        halaqah_ids=scope.halaqah_ids,
        order_collation=get_settings().arabic_collation,
    )
    return AttendanceMatrixResponse.model_validate(matrix)


@router.get("/overview", response_model=OverviewResponse, summary="مؤشرات عامة")
async def overview(
    service: ServiceDep, scope: ScopeDep, date_from: DateFrom = None, date_to: DateTo = None
) -> OverviewResponse:
    start, end = _resolve(date_from, date_to)
    return OverviewResponse.model_validate(await service.overview(start, end, scope.halaqah_ids))


@router.get(
    "/halaqah-leaderboard",
    response_model=LeaderboardResponse,
    summary="ترتيب الطلاب لكل حلقة",
)
async def halaqah_leaderboard(
    service: ServiceDep,
    scope: ScopeDep,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    top: Annotated[int, Query(ge=1, le=10, description="عدد الطلاب لكل حلقة")] = 3,
) -> LeaderboardResponse:
    start, end = _resolve(date_from, date_to)
    boards = await service.halaqah_leaderboard(start, end, top, scope.halaqah_ids)
    return LeaderboardResponse(
        date_from=start,
        date_to=end,
        items=[HalaqahLeaderboardResponse.model_validate(b) for b in boards],
    )


@router.get("/at-risk", response_model=AtRiskResponse, summary="الطلاب المتعثرون")
async def at_risk(
    service: ServiceDep, scope: ScopeDep, date_from: DateFrom = None, date_to: DateTo = None
) -> AtRiskResponse:
    start, end = _resolve(date_from, date_to)
    students = await service.at_risk(start, end, scope.halaqah_ids)
    return AtRiskResponse(
        date_from=start,
        date_to=end,
        items=[AtRiskStudentResponse.model_validate(s) for s in students],
    )
