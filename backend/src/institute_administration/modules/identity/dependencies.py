"""Identity presentation: dependency wiring and authentication guards.

Other modules import :data:`CurrentUser` and :func:`require_roles` from here to
protect their endpoints.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from institute_administration.api.dependencies import DbSession
from institute_administration.core.config import Settings, get_settings
from institute_administration.modules.identity.domain import (
    InvalidCredentialsError,
    User,
    UserRepository,
    UserRole,
)
from institute_administration.modules.identity.repository import SqlAlchemyUserRepository
from institute_administration.modules.identity.service import AuthService, UserService
from institute_administration.shared.application.exceptions import AuthorizationError

_bearer_scheme = HTTPBearer(auto_error=False, description="رمز الوصول (JWT)")


def get_user_repository(session: DbSession) -> UserRepository:
    return SqlAlchemyUserRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_user_service(repository: UserRepositoryDep) -> UserService:
    return UserService(repository)


def get_auth_service(repository: UserRepositoryDep) -> AuthService:
    settings: Settings = get_settings()
    return AuthService(repository, settings)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    auth_service: AuthServiceDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise InvalidCredentialsError("يلزم تسجيل الدخول")
    return await auth_service.resolve_access_token(credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    """Build a dependency that allows only users holding one of ``roles``."""

    async def _guard(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise AuthorizationError("ليس لديك صلاحية للقيام بهذا الإجراء")
        return current_user

    return _guard


# Convenience guard: super-admin-only endpoints (management operations).
CurrentSuperAdmin = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))]
