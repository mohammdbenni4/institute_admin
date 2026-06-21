"""Halaqahs application layer: CRUD use cases."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from institute_administration.modules.halaqahs.domain import (
    Halaqah,
    HalaqahNotFoundError,
    HalaqahRepository,
    HalaqahView,
)
from institute_administration.shared.application.pagination import Page
from institute_administration.shared.application.sentinels import UNSET, Unset


@dataclass(frozen=True)
class CreateHalaqahInput:
    name: str
    teacher_id: UUID
    halaqah_type_id: UUID
    level: str | None = None
    age: str | None = None
    time_id: UUID | None = None


@dataclass(frozen=True)
class UpdateHalaqahInput:
    name: str | Unset = UNSET
    teacher_id: UUID | Unset = UNSET
    halaqah_type_id: UUID | Unset = UNSET
    level: str | None | Unset = UNSET
    age: str | None | Unset = UNSET
    time_id: UUID | None | Unset = UNSET


class HalaqahService:
    def __init__(self, halaqahs: HalaqahRepository) -> None:
        self._halaqahs = halaqahs

    async def create(self, data: CreateHalaqahInput) -> HalaqahView:
        halaqah = Halaqah.create(
            name=data.name,
            teacher_id=data.teacher_id,
            halaqah_type_id=data.halaqah_type_id,
            level=data.level,
            age=data.age,
            time_id=data.time_id,
        )
        await self._halaqahs.add(halaqah)
        return await self._require_view(halaqah.id)

    async def get(self, halaqah_id: UUID) -> HalaqahView:
        return await self._require_view(halaqah_id)

    async def list(
        self, page: Page, *, teacher_id: UUID | None = None
    ) -> tuple[list[HalaqahView], int]:
        views = await self._halaqahs.list_views(page, teacher_id=teacher_id)
        total = await self._halaqahs.count(teacher_id=teacher_id)
        return views, total

    async def update(self, halaqah_id: UUID, data: UpdateHalaqahInput) -> HalaqahView:
        halaqah = await self._halaqahs.get_entity(halaqah_id)
        if halaqah is None:
            raise HalaqahNotFoundError
        if data.name is not UNSET:
            halaqah.name = data.name.strip()
        if data.teacher_id is not UNSET:
            halaqah.teacher_id = data.teacher_id
        if data.halaqah_type_id is not UNSET:
            halaqah.halaqah_type_id = data.halaqah_type_id
        if data.level is not UNSET:
            halaqah.level = data.level
        if data.age is not UNSET:
            halaqah.age = data.age
        if data.time_id is not UNSET:
            halaqah.time_id = data.time_id
        await self._halaqahs.update(halaqah)
        return await self._require_view(halaqah_id)

    async def delete(self, halaqah_id: UUID) -> None:
        halaqah = await self._halaqahs.get_entity(halaqah_id)
        if halaqah is None:
            raise HalaqahNotFoundError
        await self._halaqahs.delete(halaqah)

    async def _require_view(self, halaqah_id: UUID) -> HalaqahView:
        view = await self._halaqahs.get_view(halaqah_id)
        if view is None:
            raise HalaqahNotFoundError
        return view
