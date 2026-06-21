"""Identity presentation: authentication and user-management endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from institute_administration.modules.identity.dependencies import (
    AuthServiceDep,
    CurrentUser,
    UserServiceDep,
    require_roles,
)
from institute_administration.modules.identity.domain import Page, UserRole
from institute_administration.modules.identity.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from institute_administration.modules.identity.service import (
    CreateUserInput,
    UpdateUserInput,
)

# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #
auth_router = APIRouter(prefix="/auth", tags=["المصادقة"])


@auth_router.post("/login", response_model=TokenResponse, summary="تسجيل الدخول")
async def login(payload: LoginRequest, auth_service: AuthServiceDep) -> TokenResponse:
    tokens = await auth_service.login(payload.email, payload.password)
    return TokenResponse(**tokens.__dict__)


@auth_router.post("/refresh", response_model=TokenResponse, summary="تجديد رمز الوصول")
async def refresh(payload: RefreshRequest, auth_service: AuthServiceDep) -> TokenResponse:
    tokens = await auth_service.refresh(payload.refresh_token)
    return TokenResponse(**tokens.__dict__)


@auth_router.get("/me", response_model=UserResponse, summary="بيانات المستخدم الحالي")
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.from_entity(current_user)


# --------------------------------------------------------------------------- #
# User management (super-admin only)
# --------------------------------------------------------------------------- #
users_router = APIRouter(
    prefix="/users",
    tags=["المستخدمون"],
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)


@users_router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء مستخدم",
)
async def create_user(payload: UserCreateRequest, service: UserServiceDep) -> UserResponse:
    user = await service.create(
        CreateUserInput(
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            role=payload.role,
            date_of_birth=payload.date_of_birth,
            is_active=payload.is_active,
        )
    )
    return UserResponse.from_entity(user)


@users_router.get("", response_model=UserListResponse, summary="قائمة المستخدمين")
async def list_users(
    service: UserServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UserListResponse:
    users, total = await service.list(Page(limit=limit, offset=offset))
    return UserListResponse(
        items=[UserResponse.from_entity(u) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@users_router.get("/{user_id}", response_model=UserResponse, summary="عرض مستخدم")
async def get_user(user_id: UUID, service: UserServiceDep) -> UserResponse:
    return UserResponse.from_entity(await service.get(user_id))


@users_router.patch("/{user_id}", response_model=UserResponse, summary="تعديل مستخدم")
async def update_user(
    user_id: UUID, payload: UserUpdateRequest, service: UserServiceDep
) -> UserResponse:
    data = payload.model_dump(exclude_unset=True)
    user = await service.update(user_id, UpdateUserInput(**data))
    return UserResponse.from_entity(user)


@users_router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف مستخدم",
)
async def delete_user(user_id: UUID, service: UserServiceDep) -> None:
    await service.delete(user_id)
