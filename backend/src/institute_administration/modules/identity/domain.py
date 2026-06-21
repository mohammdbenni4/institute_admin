"""Identity domain layer: the ``User`` aggregate, its value objects, the
repository port, and context-specific errors.

Pure business logic — no framework, ORM or HTTP imports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from institute_administration.shared.application.exceptions import AuthenticationError
from institute_administration.shared.application.pagination import Page
from institute_administration.shared.domain import (
    AggregateRoot,
    BusinessRuleViolationError,
    ConflictError,
    EntityNotFoundError,
    ValueObject,
)

__all__ = [
    "Email",
    "EmailAlreadyExistsError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "Page",
    "User",
    "UserNotFoundError",
    "UserRepository",
    "UserRole",
]


class UserRole(StrEnum):
    """Roles a user may hold. Only super admins and teachers exist today."""

    SUPER_ADMIN = "super_admin"
    TEACHER = "teacher"


@dataclass(frozen=True, slots=True)
class Email(ValueObject):
    """A normalised email address (trimmed, lower-cased)."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if "@" not in normalized or "." not in normalized.split("@")[-1]:
            raise BusinessRuleViolationError("البريد الإلكتروني غير صالح")
        object.__setattr__(self, "value", normalized)


class User(AggregateRoot[UUID]):
    """A person who can authenticate against the system."""

    def __init__(
        self,
        *,
        id: UUID,
        full_name: str,
        email: Email,
        password_hash: str,
        role: UserRole,
        date_of_birth: date | None = None,
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.full_name = full_name
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.date_of_birth = date_of_birth
        self.is_active = is_active
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(
        cls,
        *,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole,
        date_of_birth: date | None = None,
        is_active: bool = True,
    ) -> User:
        return cls(
            id=uuid4(),
            full_name=full_name.strip(),
            email=Email(email),
            password_hash=password_hash,
            role=role,
            date_of_birth=date_of_birth,
            is_active=is_active,
        )

    def rename(self, full_name: str) -> None:
        self.full_name = full_name.strip()

    def change_email(self, email: str) -> None:
        self.email = Email(email)

    def set_password_hash(self, password_hash: str) -> None:
        self.password_hash = password_hash

    def change_role(self, role: UserRole) -> None:
        self.role = role

    def set_date_of_birth(self, date_of_birth: date | None) -> None:
        self.date_of_birth = date_of_birth

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False

    @property
    def is_super_admin(self) -> bool:
        return self.role is UserRole.SUPER_ADMIN


# --------------------------------------------------------------------------- #
# Repository port
# --------------------------------------------------------------------------- #
class UserRepository(ABC):
    """Persistence port for the ``User`` aggregate."""

    @abstractmethod
    async def add(self, user: User) -> None: ...

    @abstractmethod
    async def update(self, user: User) -> None: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def exists_by_email(self, email: str, *, exclude_id: UUID | None = None) -> bool: ...

    @abstractmethod
    async def list(self, page: Page) -> list[User]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def delete(self, user: User) -> None: ...


# --------------------------------------------------------------------------- #
# Context-specific errors (mapped to HTTP status codes by the API layer)
# --------------------------------------------------------------------------- #
class UserNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "المستخدم غير موجود") -> None:
        super().__init__(message)


class EmailAlreadyExistsError(ConflictError):
    def __init__(self, message: str = "البريد الإلكتروني مستخدم بالفعل") -> None:
        super().__init__(message)


class InvalidCredentialsError(AuthenticationError):
    def __init__(self, message: str = "البريد الإلكتروني أو كلمة المرور غير صحيحة") -> None:
        super().__init__(message)


class InactiveUserError(AuthenticationError):
    def __init__(self, message: str = "تم تعطيل هذا الحساب") -> None:
        super().__init__(message)
