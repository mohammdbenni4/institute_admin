"""Halaqah-type infrastructure: SQLAlchemy repository implementation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.core.config import get_settings
from institute_administration.modules.halaqah_types.domain import (
    HalaqahType,
    HalaqahTypeRepository,
)
from institute_administration.modules.halaqah_types.models import HalaqahTypeModel
from institute_administration.shared.application.pagination import Page


def _to_entity(model: HalaqahTypeModel) -> HalaqahType:
    return HalaqahType(
        id=model.id,
        name=model.name,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyHalaqahTypeRepository(HalaqahTypeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_collation = get_settings().arabic_collation

    async def add(self, halaqah_type: HalaqahType) -> None:
        self._session.add(HalaqahTypeModel(id=halaqah_type.id, name=halaqah_type.name))
        await self._session.flush()

    async def update(self, halaqah_type: HalaqahType) -> None:
        model = await self._session.get(HalaqahTypeModel, halaqah_type.id)
        if model is None:  # pragma: no cover - guarded by the service layer
            return
        model.name = halaqah_type.name
        await self._session.flush()

    async def get_by_id(self, type_id: UUID) -> HalaqahType | None:
        model = await self._session.get(HalaqahTypeModel, type_id)
        return _to_entity(model) if model else None

    async def exists_by_name(self, name: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(HalaqahTypeModel.id).where(HalaqahTypeModel.name == name.strip())
        if exclude_id is not None:
            stmt = stmt.where(HalaqahTypeModel.id != exclude_id)
        result = await self._session.execute(stmt.limit(1))
        return result.first() is not None

    async def list(self, page: Page) -> list[HalaqahType]:
        result = await self._session.execute(
            select(HalaqahTypeModel)
            .order_by(HalaqahTypeModel.name.collate(self._order_collation))
            .limit(page.limit)
            .offset(page.offset)
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(HalaqahTypeModel))
        return int(result.scalar_one())

    async def delete(self, halaqah_type: HalaqahType) -> None:
        model = await self._session.get(HalaqahTypeModel, halaqah_type.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
