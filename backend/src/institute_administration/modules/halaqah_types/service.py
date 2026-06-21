"""Halaqah-type application layer: CRUD use cases."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from institute_administration.modules.halaqah_types.domain import (
    HalaqahType,
    HalaqahTypeNameAlreadyExistsError,
    HalaqahTypeNotFoundError,
    HalaqahTypeRepository,
)
from institute_administration.shared.application.pagination import Page
from institute_administration.shared.application.sentinels import UNSET, Unset


@dataclass(frozen=True)
class CreateHalaqahTypeInput:
    name: str


@dataclass(frozen=True)
class UpdateHalaqahTypeInput:
    name: str | Unset = UNSET


class HalaqahTypeService:
    def __init__(self, halaqah_types: HalaqahTypeRepository) -> None:
        self._types = halaqah_types

    async def create(self, data: CreateHalaqahTypeInput) -> HalaqahType:
        if await self._types.exists_by_name(data.name):
            raise HalaqahTypeNameAlreadyExistsError
        halaqah_type = HalaqahType.create(name=data.name)
        await self._types.add(halaqah_type)
        return await self.get(halaqah_type.id)

    async def get(self, type_id: UUID) -> HalaqahType:
        halaqah_type = await self._types.get_by_id(type_id)
        if halaqah_type is None:
            raise HalaqahTypeNotFoundError
        return halaqah_type

    async def list(self, page: Page) -> tuple[list[HalaqahType], int]:
        return await self._types.list(page), await self._types.count()

    async def update(self, type_id: UUID, data: UpdateHalaqahTypeInput) -> HalaqahType:
        halaqah_type = await self.get(type_id)
        if data.name is not UNSET:
            if await self._types.exists_by_name(data.name, exclude_id=type_id):
                raise HalaqahTypeNameAlreadyExistsError
            halaqah_type.rename(data.name)
        await self._types.update(halaqah_type)
        return await self.get(type_id)

    async def delete(self, type_id: UUID) -> None:
        halaqah_type = await self.get(type_id)
        await self._types.delete(halaqah_type)
