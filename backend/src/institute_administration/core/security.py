"""Security primitives: password hashing (argon2) and JWT tokens.

This module is intentionally framework-agnostic and stateless — it knows nothing
about HTTP or the database. The presentation layer wires it into FastAPI
dependencies, and the application layer uses it to hash/verify credentials.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from institute_administration.core.config import Settings

_password_hasher = PasswordHash.recommended()


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(Exception):
    """Raised when a JWT cannot be decoded or fails validation."""


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with argon2."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its stored hash."""
    return _password_hasher.verify(plain_password, password_hash)


def _create_token(
    *,
    subject: UUID,
    token_type: TokenType,
    expires_delta: timedelta,
    settings: Settings,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: UUID,
    settings: Settings,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    return _create_token(
        subject=subject,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        settings=settings,
        extra_claims=extra_claims,
    )


def create_refresh_token(subject: UUID, settings: Settings) -> str:
    return _create_token(
        subject=subject,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        settings=settings,
    )


def decode_token(token: str, settings: Settings, expected_type: TokenType) -> UUID:
    """Decode a JWT, validate its type, and return the subject (user id)."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("الرمز غير صالح أو منتهي الصلاحية") from exc

    if payload.get("type") != expected_type.value:
        raise InvalidTokenError("نوع الرمز غير صحيح")

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("الرمز لا يحتوي على معرّف المستخدم")
    try:
        return UUID(subject)
    except (ValueError, TypeError) as exc:
        raise InvalidTokenError("معرّف المستخدم في الرمز غير صالح") from exc
