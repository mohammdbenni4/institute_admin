"""Unit tests for domain value objects (Email, TimeRange)."""

from __future__ import annotations

import pytest

from institute_administration.modules.identity.domain import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    Email,
    RawPassword,
    WeakPasswordError,
)
from institute_administration.modules.times.domain import TimeRange
from institute_administration.shared.domain import BusinessRuleViolationError

pytestmark = pytest.mark.unit


class TestRawPassword:
    def test_accepts_a_compliant_password(self) -> None:
        assert RawPassword("s3cret!").value == "s3cret!"

    def test_keeps_value_verbatim(self) -> None:
        # Passwords may legitimately contain spaces; they must not be trimmed.
        secret = "  spaced  "
        assert RawPassword(secret).value == secret

    def test_rejects_a_password_shorter_than_the_minimum(self) -> None:
        with pytest.raises(WeakPasswordError):
            RawPassword("a" * (PASSWORD_MIN_LENGTH - 1))

    def test_rejects_an_empty_password(self) -> None:
        with pytest.raises(WeakPasswordError):
            RawPassword("")

    def test_rejects_a_password_longer_than_the_maximum(self) -> None:
        with pytest.raises(WeakPasswordError):
            RawPassword("a" * (PASSWORD_MAX_LENGTH + 1))

    def test_too_short_message_states_the_required_length(self) -> None:
        with pytest.raises(WeakPasswordError, match=str(PASSWORD_MIN_LENGTH)):
            RawPassword("abc")

    def test_is_a_business_rule_violation(self) -> None:
        # The API layer maps BusinessRuleViolationError onto a 422 with a string
        # detail, which is what surfaces the Arabic reason to the user.
        assert issubclass(WeakPasswordError, BusinessRuleViolationError)


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
