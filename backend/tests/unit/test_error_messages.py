"""Every validation failure a user can trigger must read as Arabic.

A teacher once saw «exam_total: Input should be a valid integer, got a number with
a fractional part» on their phone, because the field had no Arabic label and the
error type had no template. These tests pin both halves down.
"""

from __future__ import annotations

import pytest
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from institute_administration.api.error_handlers import (
    _describe_location,
    _error_code,
    _validation_errors,
)
from institute_administration.modules.daily_records.schemas import BulkUpsertItem, BulkUpsertRequest

pytestmark = pytest.mark.unit

ARABIC = set("أبتثجحخدذرزسشصضطظعغفقكلمنهويءآإئؤىة ")


def _rendered(**kwargs: object) -> tuple[str, list[dict[str, object]]]:
    """Run a payload through the schema and render it the way the API does."""
    try:
        BulkUpsertItem(**kwargs)  # type: ignore[arg-type]
    except ValidationError as exc:
        return _validation_errors(RequestValidationError(exc.errors()))
    raise AssertionError("expected the payload to be rejected")


def _detail(**kwargs: object) -> str:
    return _rendered(**kwargs)[0]


def _is_arabic(text: str) -> bool:
    """No Latin letters leaked through from a validator's own message."""
    return not any(ch.isascii() and ch.isalpha() for ch in text)


def test_half_a_page_is_now_accepted() -> None:
    """«نصف صفحة» is a real entry — the column is decimal, so 0.5 must be valid."""
    item = BulkUpsertItem(
        student_id="0f14d0ab-9605-4a62-a9e4-5ed26688389b",
        record_date="2026-08-02",
        exam_total=0.5,
    )
    assert item.exam_total == 0.5


def test_a_page_count_beyond_the_limit_is_explained_in_arabic() -> None:
    detail = _detail(
        student_id="0f14d0ab-9605-4a62-a9e4-5ed26688389b",
        record_date="2026-08-02",
        exam_total=100000,
    )
    assert "العدد الكلي" in detail
    assert _is_arabic(detail), detail


@pytest.mark.parametrize(
    ("field", "value", "expected_label"),
    [
        ("exam_from", 2.5, "التسميع من"),
        ("exam_from", "abc", "التسميع من"),
        ("rating", 9, "التقدير"),
        ("attitude", 7, "الأدب"),
        ("added_points", 5000, "النقاط الإضافية"),
        ("record_date", "not-a-date", "تاريخ السجل"),
        ("student_id", "not-a-uuid", "الطالب"),
    ],
)
def test_each_field_is_named_and_explained_in_arabic(
    field: str, value: object, expected_label: str
) -> None:
    payload: dict[str, object] = {
        "student_id": "0f14d0ab-9605-4a62-a9e4-5ed26688389b",
        "record_date": "2026-08-02",
    }
    payload[field] = value
    detail = _detail(**payload)
    assert expected_label in detail, detail
    assert _is_arabic(detail), detail


def test_a_missing_required_field_is_arabic() -> None:
    detail = _detail(record_date="2026-08-02")
    assert "الطالب" in detail and "مطلوب" in detail


def test_batch_errors_name_the_offending_record() -> None:
    """A rejected batch must say *which* entry is wrong, not just the field."""
    try:
        BulkUpsertRequest(
            halaqah_id="0f14d0ab-9605-4a62-a9e4-5ed26688389b",
            teacher_id="0f14d0ab-9605-4a62-a9e4-5ed26688389b",
            records=[
                {"student_id": "0f14d0ab-9605-4a62-a9e4-5ed26688389b", "record_date": "2026-08-02"},
                {
                    "student_id": "0f14d0ab-9605-4a62-a9e4-5ed26688389b",
                    "record_date": "2026-08-02",
                    "exam_total": 100000,
                },
            ],
        )
    except ValidationError as exc:
        detail, _ = _validation_errors(RequestValidationError(exc.errors()))
        assert "السجل رقم 2" in detail, detail
        assert "العدد الكلي" in detail
        assert _is_arabic(detail), detail
    else:  # pragma: no cover
        raise AssertionError("expected the batch to be rejected")


def test_location_without_an_index_names_only_the_field() -> None:
    assert _describe_location(("body", "exam_total")) == "العدد الكلي"


def test_unknown_field_falls_back_to_its_raw_name() -> None:
    assert _describe_location(("body", "mystery")) == "mystery"


def test_errors_carry_a_machine_readable_field_and_code() -> None:
    """The client needs to know *which input* to highlight, not just a sentence."""
    _, errors = _rendered(
        student_id="0f14d0ab-9605-4a62-a9e4-5ed26688389b",
        record_date="2026-08-02",
        rating=9,
    )
    assert errors[0]["field"] == "rating"
    assert errors[0]["label"] == "التقدير"
    assert errors[0]["code"] == "less_than_equal"
    assert _is_arabic(str(errors[0]["message"]))


def test_batch_errors_carry_the_record_index() -> None:
    try:
        BulkUpsertRequest(
            halaqah_id="0f14d0ab-9605-4a62-a9e4-5ed26688389b",
            teacher_id="0f14d0ab-9605-4a62-a9e4-5ed26688389b",
            records=[
                {"student_id": "0f14d0ab-9605-4a62-a9e4-5ed26688389b", "record_date": "2026-08-02"},
                {
                    "student_id": "0f14d0ab-9605-4a62-a9e4-5ed26688389b",
                    "record_date": "2026-08-02",
                    "rating": 99,
                },
            ],
        )
    except ValidationError as exc:
        _, errors = _validation_errors(RequestValidationError(exc.errors()))
        assert errors[0]["index"] == 1  # zero-based position of the bad record
        assert errors[0]["field"] == "rating"
    else:  # pragma: no cover
        raise AssertionError("expected the batch to be rejected")


def test_exception_class_names_become_stable_codes() -> None:
    from institute_administration.modules.daily_records.domain import LateWhileAbsentError

    assert _error_code(LateWhileAbsentError()) == "late_while_absent"
