"""Unit tests for per-student scoring: a student pinned to a named preset is priced
by it, everyone else by the institute-wide policy."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from uuid import UUID, uuid4

import pytest

from institute_administration.modules.daily_records.domain import (
    DEFAULT_SCORING,
    DailyRecord,
    DailyRecordRepository,
    ScoringPolicy,
)
from institute_administration.modules.daily_records.service import (
    DailyRecordService,
    UpsertDailyRecordEntry,
)
from institute_administration.shared.application.pagination import Page

pytestmark = pytest.mark.unit


class _FakeRepository(DailyRecordRepository):
    """In-memory stand-in: the scoring decision is what's under test, not persistence."""

    def __init__(self) -> None:
        self.records: dict[UUID, DailyRecord] = {}

    async def add(self, record: DailyRecord) -> None:
        self.records[record.id] = record

    async def update(self, record: DailyRecord) -> None:
        self.records[record.id] = record

    async def get_by_id(self, record_id: UUID) -> DailyRecord | None:
        return self.records.get(record_id)

    async def find_by_natural_keys(
        self, keys: Sequence[tuple[UUID, date]]
    ) -> dict[tuple[UUID, date], DailyRecord]:
        wanted = set(keys)
        return {
            (r.student_id, r.record_date): r
            for r in self.records.values()
            if (r.student_id, r.record_date) in wanted
        }

    async def list(self, page: Page, **kwargs: object) -> list[DailyRecord]:
        return list(self.records.values())

    async def count(self, **kwargs: object) -> int:
        return len(self.records)

    async def delete(self, record: DailyRecord) -> None:
        self.records.pop(record.id, None)

    async def latest_recitations(self, student_ids: Sequence[UUID], **kwargs: object) -> list:
        return []

    async def latest_homework(self, student_ids: Sequence[UUID], **kwargs: object) -> list:
        return []


# A preset that prices everything differently from DEFAULT_SCORING.
GENEROUS = replace(
    DEFAULT_SCORING,
    present_points=3,
    rating_points={4: 10, 3: 7, 2: 4, 1: 0},
)


class _Resolver:
    """Stands in for `StudentScoringPolicyResolver`: only `pinned` gets the preset."""

    def __init__(self, pinned: UUID) -> None:
        self._pinned = pinned
        self.primed: list[UUID] = []

    async def prime(self, student_ids: Sequence[UUID]) -> None:
        self.primed.extend(student_ids)

    async def for_student(self, student_id: UUID) -> ScoringPolicy:
        return GENEROUS if student_id == self._pinned else DEFAULT_SCORING


def _entry(student_id: UUID) -> UpsertDailyRecordEntry:
    return UpsertDailyRecordEntry(
        student_id=student_id,
        record_date=date(2026, 8, 23),
        present=True,
        rating=4,
        attitude=3,
    )


@pytest.mark.asyncio
async def test_without_a_resolver_every_record_uses_the_institute_policy() -> None:
    service = DailyRecordService(_FakeRepository())
    saved, _, _ = await service.bulk_upsert(
        halaqah_id=uuid4(), teacher_id=uuid4(), entries=[_entry(uuid4())]
    )
    assert saved[0].card_present == DEFAULT_SCORING.present_points
    assert saved[0].card_exam == DEFAULT_SCORING.rating_points[4]


@pytest.mark.asyncio
async def test_pinned_student_is_priced_by_their_preset() -> None:
    pinned, plain = uuid4(), uuid4()
    resolver = _Resolver(pinned)
    service = DailyRecordService(_FakeRepository(), DEFAULT_SCORING, resolver)

    saved, _, _ = await service.bulk_upsert(
        halaqah_id=uuid4(),
        teacher_id=uuid4(),
        entries=[_entry(pinned), _entry(plain)],
    )
    by_student = {r.student_id: r for r in saved}

    assert by_student[pinned].card_present == 3
    assert by_student[pinned].card_exam == 10
    # The same batch, the same rating — but the unpinned student keeps the defaults.
    assert by_student[plain].card_present == DEFAULT_SCORING.present_points
    assert by_student[plain].card_exam == DEFAULT_SCORING.rating_points[4]


@pytest.mark.asyncio
async def test_bulk_upsert_primes_the_resolver_once_for_the_whole_batch() -> None:
    """The batch is preloaded in one go — otherwise a 100-record upload would issue
    a query per record."""
    resolver = _Resolver(uuid4())
    service = DailyRecordService(_FakeRepository(), DEFAULT_SCORING, resolver)
    students = [uuid4() for _ in range(5)]

    await service.bulk_upsert(
        halaqah_id=uuid4(), teacher_id=uuid4(), entries=[_entry(s) for s in students]
    )
    assert resolver.primed == students


@pytest.mark.asyncio
async def test_rescoring_an_existing_record_still_uses_the_students_preset() -> None:
    """A second upload overwrites the record; it must not silently fall back to the
    institute weights on the update path."""
    pinned = uuid4()
    service = DailyRecordService(_FakeRepository(), DEFAULT_SCORING, _Resolver(pinned))
    halaqah, teacher = uuid4(), uuid4()

    await service.bulk_upsert(halaqah_id=halaqah, teacher_id=teacher, entries=[_entry(pinned)])
    saved, created, updated = await service.bulk_upsert(
        halaqah_id=halaqah, teacher_id=teacher, entries=[_entry(pinned)]
    )

    assert (created, updated) == (0, 1)
    assert saved[0].card_exam == 10
