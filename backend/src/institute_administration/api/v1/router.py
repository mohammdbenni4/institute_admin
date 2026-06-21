"""Aggregate router for API v1: mounts every bounded context's endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from institute_administration.api.v1 import health
from institute_administration.modules.analytics.router import router as analytics_router
from institute_administration.modules.daily_records.router import router as daily_records_router
from institute_administration.modules.halaqah_types.router import router as halaqah_types_router
from institute_administration.modules.halaqahs.router import router as halaqahs_router
from institute_administration.modules.identity.router import auth_router, users_router
from institute_administration.modules.scoring.router import router as scoring_router
from institute_administration.modules.students.router import router as students_router
from institute_administration.modules.teachers.router import router as teachers_router
from institute_administration.modules.times.router import router as times_router

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(teachers_router)
api_router.include_router(students_router)
api_router.include_router(halaqahs_router)
api_router.include_router(halaqah_types_router)
api_router.include_router(times_router)
api_router.include_router(daily_records_router)
api_router.include_router(analytics_router)
api_router.include_router(scoring_router)
