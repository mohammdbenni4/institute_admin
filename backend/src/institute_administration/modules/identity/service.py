"""Identity application layer: user management and authentication use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from institute_administration.core.config import Settings
from institute_administration.core.security import (
    InvalidTokenError as _InvalidTokenError,
)
from institute_administration.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from institute_administration.modules.identity.domain import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    Page,
    User,
    UserNotFoundError,
    UserRepository,
    UserRole,
)
from institute_administration.shared.application.sentinels import UNSET, Unset


@dataclass(frozen=True)
class CreateUserInput:
    full_name: str
    email: str
    password: str
    role: UserRole
    date_of_birth: date | None = None
    is_active: bool = True


@dataclass(frozen=True)
class UpdateUserInput:
    full_name: str | Unset = UNSET
    email: str | Unset = UNSET
    password: str | Unset = UNSET
    role: UserRole | Unset = UNSET
    date_of_birth: date | None | Unset = UNSET
    is_active: bool | Unset = UNSET


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserService:
    """CRUD use cases for the ``User`` aggregate."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def create(self, data: CreateUserInput) -> User:
        if await self._users.exists_by_email(data.email):
            raise EmailAlreadyExistsError
        user = User.create(
            full_name=data.full_name,
            email=data.email,
            password_hash=hash_password(data.password),
            role=data.role,
            date_of_birth=data.date_of_birth,
            is_active=data.is_active,
        )
        await self._users.add(user)
        return await self.get(user.id)

    async def get(self, user_id: UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError
        return user

    async def list(self, page: Page) -> tuple[list[User], int]:
        return await self._users.list(page), await self._users.count()

    async def update(self, user_id: UUID, data: UpdateUserInput) -> User:
        user = await self.get(user_id)

        if data.email is not UNSET and data.email != user.email.value:
            if await self._users.exists_by_email(data.email, exclude_id=user_id):
                raise EmailAlreadyExistsError
            user.change_email(data.email)
        if data.full_name is not UNSET:
            user.rename(data.full_name)
        if data.password is not UNSET:
            user.set_password_hash(hash_password(data.password))
        if data.role is not UNSET:
            user.change_role(data.role)
        if data.date_of_birth is not UNSET:
            user.set_date_of_birth(data.date_of_birth)
        if data.is_active is not UNSET:
            user.activate() if data.is_active else user.deactivate()

        await self._users.update(user)
        return await self.get(user_id)

    async def delete(self, user_id: UUID) -> None:
        user = await self.get(user_id)
        await self._users.delete(user)


class AuthService:
    """Authentication use cases: login, token refresh, and identity resolution."""

    def __init__(self, users: UserRepository, settings: Settings) -> None:
        self._users = users
        self._settings = settings

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError
        return user

    def issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(
                user.id, self._settings, extra_claims={"role": user.role.value}
            ),
            refresh_token=create_refresh_token(user.id, self._settings),
        )

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.authenticate(email, password)
        return self.issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            user_id = decode_token(refresh_token, self._settings, TokenType.REFRESH)
        except _InvalidTokenError as exc:
            raise InvalidCredentialsError(str(exc)) from exc
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError
        return self.issue_tokens(user)

    async def resolve_access_token(self, access_token: str) -> User:
        try:
            user_id = decode_token(access_token, self._settings, TokenType.ACCESS)
        except _InvalidTokenError as exc:
            raise InvalidCredentialsError(str(exc)) from exc
        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidCredentialsError
        return user
