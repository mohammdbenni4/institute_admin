"""Unit tests for domain value objects (Email, TimeRange)."""

from __future__ import annotations

import pytest

from institute_administration.modules.identity.domain import Email
from institute_administration.modules.times.domain import TimeRange
from institute_administration.shared.domain import BusinessRuleViolationError

pytestmark = pytest.mark.unit


class TestEmail:
    def test_normalises_case_and_whitespace(self) -> None:
        assert Email("  SuperAdmin@Gmail.com ").value == "superadmin@gmail.com"

    def test_equality_is_value_based(self) -> None:
        assert Email("a@b.com") == Email("A@B.COM")

    @pytest.mark.parametrize("invalid", ["", "no-at-sign", "missing@domain", "a@b"])
    def test_rejects_invalid_addresses(self, invalid: str) -> None:
        with pytest.raises(BusinessRuleViolationError):
            Email(invalid)


class TestTimeRange:
    def test_accepts_valid_range(self) -> None:
        time_range = TimeRange(start="16:00", end="18:30")
        assert (time_range.start, time_range.end) == ("16:00", "18:30")

    @pytest.mark.parametrize("bad", ["1600", "24:00", "16:60", "9:00"])
    def test_rejects_bad_format(self, bad: str) -> None:
        with pytest.raises(BusinessRuleViolationError):
            TimeRange(start=bad, end="18:00")

    def test_rejects_start_not_before_end(self) -> None:
        with pytest.raises(BusinessRuleViolationError):
            TimeRange(start="18:00", end="16:00")
