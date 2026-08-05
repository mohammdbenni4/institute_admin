"""Unit tests for the daily records domain: reward-card scoring and invariants."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from institute_administration.modules.daily_records.domain import (
    DailyRecord,
    InvalidAttitudeError,
    InvalidExamRangeError,
    InvalidRatingError,
    LateWhileAbsentError,
)

pytestmark = pytest.mark.unit


def _make(**overrides: object) -> DailyRecord:
    """Build a valid daily record, overriding individual fields per test."""
    kwargs: dict[str, object] = {
        "student_id": uuid4(),
        "teacher_id": uuid4(),
        "halaqah_id": uuid4(),
        "record_date": date(2026, 6, 18),
        "present": True,
    }
    kwargs.update(overrides)
    return DailyRecord.create(**kwargs)  # type: ignore[arg-type]


def test_card_present_is_five_when_present() -> None:
    assert _make(present=True).card_present == 5


def test_card_present_is_zero_when_absent() -> None:
    assert _make(present=False).card_present == 0


@pytest.mark.parametrize(
    ("rating", "expected"),
    [(4, 7), (3, 5), (2, 3), (1, 0), (None, 0)],
)
def test_card_exam_maps_from_rating(rating: int | None, expected: int) -> None:
    assert _make(rating=rating).card_exam == expected


@pytest.mark.parametrize(("attitude", "expected"), [(1, 1), (2, 2), (3, 3), (None, 0)])
def test_card_attitude_equals_attitude(attitude: int | None, expected: int) -> None:
    assert _make(attitude=attitude).card_attitude == expected


def test_total_points_sums_all_card_scores_plus_added_points() -> None:
    record = _make(present=True, rating=4, attitude=3, added_points=2)
    # 5 (present) + 7 (rating 4) + 3 (attitude) + 2 (added) = 17
    assert record.total_points == 17


def test_total_points_for_absent_student_counts_only_added_points() -> None:
    record = _make(present=False, added_points=4)
    assert record.card_present == 0
    assert record.card_exam == 0
    assert record.card_attitude == 0
    assert record.total_points == 4


@pytest.mark.parametrize("rating", [0, 5, -1])
def test_invalid_rating_is_rejected(rating: int) -> None:
    with pytest.raises(InvalidRatingError):
        _make(rating=rating)


@pytest.mark.parametrize("revision_rating", [0, 5])
def test_invalid_revision_rating_is_rejected(revision_rating: int) -> None:
    with pytest.raises(InvalidRatingError):
        _make(revision_rating=revision_rating)


@pytest.mark.parametrize("attitude", [0, 4, -2])
def test_invalid_attitude_is_rejected(attitude: int) -> None:
    with pytest.raises(InvalidAttitudeError):
        _make(attitude=attitude)


def test_exam_to_before_exam_from_is_rejected() -> None:
    with pytest.raises(InvalidExamRangeError):
        _make(exam_from=10, exam_to=5)


def test_negative_exam_value_is_rejected() -> None:
    with pytest.raises(InvalidExamRangeError):
        _make(exam_from=-1)


def test_added_points_may_be_negative() -> None:
    """Teachers deduct as well as award («إضافة النقاط وحذفها بشكل كامل»)."""
    record = _make(present=True, added_points=-3)
    assert record.added_points == -3
    assert record.total_points == 2  # 5 present - 3 deducted


def test_total_points_may_go_below_zero_when_deductions_exceed_earnings() -> None:
    assert _make(present=False, added_points=-4).total_points == -4


def test_late_student_is_still_present_and_scores_the_late_weight() -> None:
    record = _make(present=True, late=True)
    assert record.present is True
    assert record.card_present == 5  # DEFAULT_SCORING prices late the same as present


def test_late_cannot_be_recorded_for_an_absent_student() -> None:
    with pytest.raises(LateWhileAbsentError):
        _make(present=False, late=True)


def test_excuse_reason_is_carried_on_the_record() -> None:
    record = _make(present=False, excused=True, excuse_reason="سفر مع العائلة")
    assert record.excuse_reason == "سفر مع العائلة"


def test_revalidate_catches_post_mutation_violation() -> None:
    record = _make(rating=4)
    record.rating = 9
    with pytest.raises(InvalidRatingError):
        record.revalidate()
