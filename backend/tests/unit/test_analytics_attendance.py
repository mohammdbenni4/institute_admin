"""Unit tests for the attendance-matrix packing done by the analytics service.

The packed `days` string is what lets the admin heat-map fetch one small row per
student instead of every daily record in the month, so its alignment with the
window and its agreement with the counters are worth pinning down.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from institute_administration.modules.analytics.repository import AttendanceRow
from institute_administration.modules.analytics.service import AnalyticsService

pytestmark = pytest.mark.unit


def _row(**overrides: object) -> AttendanceRow:
    kwargs: dict[str, object] = {
        "student_id": uuid4(),
        "student_name": "طالب",
        "father_number": None,
        "halaqah_id": uuid4(),
        "halaqah_name": "حلقة",
        "teacher_id": uuid4(),
        "teacher_name": "معلم",
        "teacher_names": "معلم",
        "present": 0,
        "late": 0,
        "absent": 0,
        "excused": 0,
        "total": 0,
    }
    kwargs.update(overrides)
    return AttendanceRow(**kwargs)  # type: ignore[arg-type]


def test_days_string_spans_the_whole_window() -> None:
    packed = AnalyticsService._to_student(_row(), {}, date(2026, 6, 1), 30)
    assert len(packed.days) == 30
    assert set(packed.days) == {"."}


def test_days_string_places_each_status_on_its_own_day() -> None:
    statuses = {
        date(2026, 6, 1): "P",
        date(2026, 6, 2): "L",
        date(2026, 6, 3): "A",
        date(2026, 6, 5): "E",
    }
    packed = AnalyticsService._to_student(
        _row(present=2, late=1, absent=1, excused=1, total=4), statuses, date(2026, 6, 1), 7
    )
    assert packed.days == "PLA.E.."


def test_a_late_day_still_counts_as_attended_in_the_rate() -> None:
    """`L` marks the day on the heat-map, but the student did attend."""
    packed = AnalyticsService._to_student(
        _row(present=2, late=1, total=2),
        {date(2026, 6, 1): "L", date(2026, 6, 2): "P"},
        date(2026, 6, 1),
        2,
    )
    assert packed.late == 1
    assert packed.rate == 100


def test_days_string_is_offset_from_the_window_start_not_the_month() -> None:
    """A report window may start mid-month; index 0 is the window's first day."""
    packed = AnalyticsService._to_student(
        _row(present=1, total=1), {date(2026, 6, 10): "P"}, date(2026, 6, 8), 5
    )
    assert packed.days == "..P.."


def test_rate_is_a_rounded_percentage_of_recorded_days() -> None:
    packed = AnalyticsService._to_student(
        _row(present=2, absent=1, total=3), {}, date(2026, 6, 1), 3
    )
    assert packed.rate == 67


def test_rate_is_zero_when_nothing_was_recorded() -> None:
    packed = AnalyticsService._to_student(_row(), {}, date(2026, 6, 1), 3)
    assert packed.rate == 0
