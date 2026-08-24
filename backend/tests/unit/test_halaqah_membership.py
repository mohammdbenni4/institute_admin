"""Unit tests for teacher ↔ halaqah membership orchestration.

A halaqah has many teachers and a teacher has many halaqahs. The membership table
is what access control reads, and ``halaqahs.teacher_id`` only names the
responsible teacher whose name the paper report prints.

These cover the ordering the service is responsible for; the database-level
invariant (the responsible teacher can never be removed from the membership) is
enforced in the repository and exercised against a real database.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest

from institute_administration.modules.halaqahs.domain import (
    Halaqah,
    HalaqahRepository,
    HalaqahView,
    TeacherBrief,
)
from institute_administration.modules.halaqahs.service import (
    CreateHalaqahInput,
    HalaqahService,
    UpdateHalaqahInput,
)
from institute_administration.shared.application.pagination import Page

pytestmark = pytest.mark.unit


class _FakeRepository(HalaqahRepository):
    """Records the calls the service makes, in order."""

    def __init__(self) -> None:
        self.entities: dict[UUID, Halaqah] = {}
        self.members: dict[UUID, set[UUID]] = {}
        self.calls: list[str] = []

    async def add(self, halaqah: Halaqah) -> None:
        self.calls.append("add")
        self.entities[halaqah.id] = halaqah
        # Mirrors the real repository: creating a halaqah makes its responsible
        # teacher a member straight away.
        self.members[halaqah.id] = {halaqah.teacher_id}

    async def update(self, halaqah: Halaqah) -> None:
        self.calls.append("update")
        self.entities[halaqah.id] = halaqah
        self.members.setdefault(halaqah.id, set()).add(halaqah.teacher_id)

    async def set_teachers(self, halaqah_id: UUID, teacher_ids: Sequence[UUID]) -> None:
        self.calls.append("set_teachers")
        responsible = self.entities[halaqah_id].teacher_id
        self.members[halaqah_id] = {responsible, *teacher_ids}

    async def get_entity(self, halaqah_id: UUID) -> Halaqah | None:
        return self.entities.get(halaqah_id)

    async def get_view(self, halaqah_id: UUID) -> HalaqahView | None:
        entity = self.entities.get(halaqah_id)
        if entity is None:
            return None
        members = sorted(self.members.get(halaqah_id, set()), key=str)
        return HalaqahView(
            id=entity.id,
            name=entity.name,
            level=None,
            age=None,
            teacher_id=entity.teacher_id,
            teacher_name="معلم",
            teachers=tuple(TeacherBrief(id=t, name="معلم") for t in members),
            halaqah_type_id=entity.halaqah_type_id,
            halaqah_type_name="حفظ",
            time_id=None,
            time_name=None,
            schedule={},
            number_of_students=0,
            created_at=None,  # type: ignore[arg-type]
            updated_at=None,  # type: ignore[arg-type]
        )

    async def list_views(self, page: Page, *, teacher_id: UUID | None = None) -> list[HalaqahView]:
        return []

    async def count(self, *, teacher_id: UUID | None = None) -> int:
        return 0

    async def ids_for_teacher(self, teacher_id: UUID) -> set[UUID]:
        return {hid for hid, members in self.members.items() if teacher_id in members}

    async def delete(self, halaqah: Halaqah) -> None:
        self.entities.pop(halaqah.id, None)
        self.members.pop(halaqah.id, None)


def _create(**overrides: object) -> CreateHalaqahInput:
    kwargs: dict[str, object] = {
        "name": "حلقة",
        "teacher_id": uuid4(),
        "halaqah_type_id": uuid4(),
    }
    kwargs.update(overrides)
    return CreateHalaqahInput(**kwargs)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_a_new_halaqah_has_its_responsible_teacher_as_a_member() -> None:
    repo = _FakeRepository()
    view = await HalaqahService(repo).create(_create())
    assert repo.members[view.id] == {view.teacher_id}


@pytest.mark.asyncio
async def test_additional_teachers_are_members_alongside_the_responsible_one() -> None:
    repo = _FakeRepository()
    extra_a, extra_b = uuid4(), uuid4()
    view = await HalaqahService(repo).create(_create(teacher_ids=[extra_a, extra_b]))
    assert repo.members[view.id] == {view.teacher_id, extra_a, extra_b}


@pytest.mark.asyncio
async def test_omitting_teacher_ids_leaves_membership_untouched() -> None:
    """A PATCH that only renames a halaqah must not silently unassign its teachers."""
    repo = _FakeRepository()
    service = HalaqahService(repo)
    extra = uuid4()
    view = await service.create(_create(teacher_ids=[extra]))

    await service.update(view.id, UpdateHalaqahInput(name="اسم جديد"))

    assert repo.members[view.id] == {view.teacher_id, extra}
    assert "set_teachers" not in repo.calls[2:]  # only the one from create()


@pytest.mark.asyncio
async def test_sending_teacher_ids_replaces_membership() -> None:
    repo = _FakeRepository()
    service = HalaqahService(repo)
    old_extra, new_extra = uuid4(), uuid4()
    view = await service.create(_create(teacher_ids=[old_extra]))

    await service.update(view.id, UpdateHalaqahInput(teacher_ids=[new_extra]))

    assert repo.members[view.id] == {view.teacher_id, new_extra}
    assert old_extra not in repo.members[view.id]


@pytest.mark.asyncio
async def test_membership_is_replaced_after_the_responsible_teacher_changes() -> None:
    """Ordering matters.

    If membership were replaced *before* the halaqah's own update, the incoming
    list would be reconciled against the *old* responsible teacher — keeping
    someone who no longer leads the halaqah and, worse, leaving the new
    responsible teacher without access to a halaqah the report names them on.
    """
    repo = _FakeRepository()
    service = HalaqahService(repo)
    view = await service.create(_create())
    new_responsible, helper = uuid4(), uuid4()

    await service.update(
        view.id, UpdateHalaqahInput(teacher_id=new_responsible, teacher_ids=[helper])
    )

    assert repo.calls[-2:] == ["update", "set_teachers"]
    assert repo.members[view.id] == {new_responsible, helper}


@pytest.mark.asyncio
async def test_a_teacher_reaches_every_halaqah_they_are_a_member_of() -> None:
    """The scope of a teacher is the union of the halaqahs they lead and assist."""
    repo = _FakeRepository()
    service = HalaqahService(repo)
    helper = uuid4()

    led = await service.create(_create())
    assisted = await service.create(_create(teacher_ids=[helper]))
    unrelated = await service.create(_create())

    assert await repo.ids_for_teacher(led.teacher_id) == {led.id}
    assert await repo.ids_for_teacher(helper) == {assisted.id}
    assert unrelated.id not in await repo.ids_for_teacher(helper)
