"""Identity infrastructure: SQLAlchemy implementation of ``UserRepository``."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.core.config import get_settings
from institute_administration.modules.identity.domain import (
    Email,
    Page,
    User,
    UserRepository,
)
from institute_administration.modules.identity.models import UserModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        full_name=model.full_name,
        email=Email(model.email),
        password_hash=model.password_hash,
        role=model.role,
        date_of_birth=model.date_of_birth,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply(model: UserModel, user: User) -> None:
    model.full_name = user.full_name
    model.email = user.email.value
    model.password_hash = user.password_hash
    model.role = user.role
    model.date_of_birth = user.date_of_birth
    model.is_active = user.is_active


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_collation = get_settings().arabic_collation

    async def add(self, user: User) -> None:
        model = UserModel(id=user.id)
        _apply(model, user)
        self._session.add(model)
        await self._session.flush()

    async def update(self, user: User) -> None:
        model = await self._session.get(UserModel, user.id)
        if model is None:  # pragma: no cover - guarded by the service layer
            return
        _apply(model, user)
        await self._session.flush()

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email.strip().lower())
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def exists_by_email(self, email: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(UserModel.id).where(UserModel.email == email.strip().lower())
        if exclude_id is not None:
            stmt = stmt.where(UserModel.id != exclude_id)
        result = await self._session.execute(stmt.limit(1))
        return result.first() is not None

    async def list(self, page: Page) -> list[User]:
        result = await self._session.execute(
            select(UserModel)
            .order_by(UserModel.full_name.collate(self._order_collation))
            .limit(page.limit)
            .offset(page.offset)
        )
        return [_to_entity(model) for model in result.scalars().all()]

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(UserModel))
        return int(result.scalar_one())

    async def delete(self, user: User) -> None:
        model = await self._session.get(UserModel, user.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
