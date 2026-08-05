"""Translation of domain/application errors into HTTP responses.

Keeping this mapping in one place means the domain and application layers stay
free of any HTTP concerns: they raise meaningful exceptions, and this module
decides how each maps onto the transport.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from institute_administration.api.rate_limit import (
    RateLimitExceededError,
    rate_limited_response,
)
from institute_administration.shared.application.exceptions import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
)
from institute_administration.shared.domain.exceptions import (
    BusinessRuleViolationError,
    ConflictError,
    DomainError,
    EntityNotFoundError,
)

# Arabic labels for every request field the apps send, so a malformed request
# explains *which* field and *why* — never a bare English validation dump. A field
# missing from here falls back to its raw name, which is how
# «exam_total: Input should be a valid integer…» once reached a teacher's phone.
_FIELD_LABELS: dict[str, str] = {
    # identity / users
    "full_name": "الاسم الكامل",
    "email": "البريد الإلكتروني",
    "password": "كلمة المرور",
    "role": "الدور",
    "is_active": "الحالة",
    # teachers & students
    "date_of_birth": "تاريخ الميلاد",
    "academic_study": "المؤهل الأكاديمي",
    "islamic_study": "المؤهل الشرعي",
    "is_assistant": "معلم مساعد",
    "father_name": "اسم الأب",
    "father_number": "رقم الأب",
    "residential_area": "منطقة السكن",
    "accepted_at": "تاريخ القبول",
    "orphan_of": "حالة اليتم",
    # halaqahs / times
    "name": "الاسم",
    "level": "المستوى",
    "age": "الفئة العمرية",
    "teacher_id": "المعلم",
    "student_id": "الطالب",
    "halaqah_id": "الحلقة",
    "halaqah_type_id": "نوع الحلقة",
    "time_id": "الوقت",
    "from": "من الساعة",
    "to": "إلى الساعة",
    # daily records
    "record_date": "تاريخ السجل",
    "present": "الحضور",
    "excused": "الإذن",
    "late": "التأخير",
    "excuse_reason": "سبب الإذن",
    "exam_from": "التسميع من",
    "exam_to": "التسميع إلى",
    "exam_total": "العدد الكلي",
    "rating": "التقدير",
    "revision_lesson": "المراجعة",
    "revision_rating": "تقييم المراجعة",
    "attitude": "الأدب",
    "added_points": "النقاط الإضافية",
    "homework": "الواجب",
    "notes": "الملاحظات",
    "problems": "الصعوبات",
    "problem_ids": "الصعوبات المحددة",
    "records": "السجلات",
    "entries": "السجلات",
    # scoring / institute
    "present_points": "نقاط الحضور",
    "absent_points": "نقاط الغياب",
    "excused_points": "نقاط الإذن",
    "late_points": "نقاط التأخير",
    "subtitle": "العبارة تحت الاسم",
    "phone": "رقم المعهد",
    "logo_url": "الشعار",
    "report_footer": "تذييل التقرير",
    "report_note": "ملاحظة الإدارة",
    # parent summons / upcoming exams
    "reason": "سبب الاستدعاء",
    "status": "الحالة",
    "admin_response": "رد الإدارة",
    "scheduled_date": "تاريخ الاختبار",
    "part": "الجزء",
}

# Arabic templates keyed by Pydantic v2 error type. Anything unmapped still falls
# back to the validator's own message, but the common cases must never do that:
# the teacher app surfaces this text verbatim.
_ERROR_TEMPLATES: dict[str, str] = {
    "missing": "هذا الحقل مطلوب",
    "string_too_short": "أقصر من الحد المسموح",
    "string_too_long": "أطول من الحد المسموح",
    "extra_forbidden": "حقل غير مسموح به",
    "value_error": "قيمة غير صالحة",
    # numbers — `int_from_float` is what a teacher typing «0.5» triggers.
    "int_from_float": "يجب أن يكون رقماً صحيحاً بدون فاصلة عشرية",
    "int_parsing": "يجب أن يكون رقماً صحيحاً",
    "int_type": "يجب أن يكون رقماً صحيحاً",
    "float_parsing": "يجب أن يكون رقماً",
    "decimal_parsing": "يجب أن يكون رقماً",
    "greater_than": "أصغر من الحد المسموح",
    "greater_than_equal": "أصغر من الحد المسموح",
    "less_than": "أكبر من الحد المسموح",
    "less_than_equal": "أكبر من الحد المسموح",
    # text / identifiers
    "string_type": "يجب أن يكون نصاً",
    "string_pattern_mismatch": "الصيغة غير صحيحة",
    "uuid_parsing": "معرّف غير صالح",
    "uuid_type": "معرّف غير صالح",
    "bool_parsing": "يجب أن يكون نعم أو لا",
    "bool_type": "يجب أن يكون نعم أو لا",
    # dates
    "date_parsing": "تاريخ غير صالح",
    "date_type": "تاريخ غير صالح",
    "date_from_datetime_parsing": "تاريخ غير صالح",
    "datetime_parsing": "تاريخ غير صالح",
    # collections & choices
    "too_short": "عدد العناصر أقل من الحد المسموح",
    "too_long": "عدد العناصر أكثر من الحد المسموح",
    "list_type": "قيمة غير صالحة",
    "enum": "قيمة غير مسموح بها",
    "literal_error": "قيمة غير مسموح بها",
    "json_invalid": "صيغة البيانات غير صالحة",
}


def _error_code(exc: Exception) -> str:
    """`LateWhileAbsentError` -> `late_while_absent`.

    A stable, machine-readable name for the failure, so a client can react to it
    (highlight a field, offer a specific fix) instead of pattern-matching Arabic
    prose that we are free to reword at any time.
    """
    name = type(exc).__name__.removesuffix("Error")
    out: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i:
            out.append("_")
        out.append(ch.lower())
    return "".join(out) or "error"


def _problem(
    status_code: int,
    title: str,
    detail: str,
    *,
    code: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Return an RFC 9457-style problem response.

    `detail` is the Arabic sentence meant for a human; `code` and `errors` are for
    the client to act on.
    """
    content: dict[str, Any] = {
        "title": title,
        "status": status_code,
        "detail": detail,
        "code": code,
    }
    if errors:
        content["errors"] = errors
    return JSONResponse(status_code=status_code, content=content)


def _describe_location(loc: tuple[Any, ...]) -> str:
    """Human Arabic description of *where* the bad value is.

    Batch endpoints nest their errors (``body.records[2].exam_total``); naming only
    the leaf leaves the teacher guessing which of twenty records to fix, so the
    1-based position is kept when there is one.
    """
    parts = [p for p in loc if p != "body"]
    field = ""
    index: int | None = None
    for part in parts:
        if isinstance(part, int):
            index = part + 1  # humans count from one
        else:
            field = str(part)
    label = _FIELD_LABELS.get(field, field)
    if index is not None and label:
        return f"السجل رقم {index} — {label}"
    if index is not None:
        return f"السجل رقم {index}"
    return label


def _validation_errors(exc: RequestValidationError) -> tuple[str, list[dict[str, Any]]]:
    """Arabic sentence for the user, plus a per-field list for the client.

    The structured half lets the teacher app put the message on the exact input
    that is wrong, and `index` identifies which record of a batch upload failed.
    """
    messages: list[str] = []
    details: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        where = _describe_location(loc)
        leaf = next((str(p) for p in reversed(loc) if not isinstance(p, int)), "")
        index = next((p for p in reversed(loc) if isinstance(p, int)), None)
        if leaf == "email":  # the email validator's own message is English
            reason = "بريد إلكتروني غير صالح"
        else:
            reason = _ERROR_TEMPLATES.get(err.get("type", ""), err.get("msg", "قيمة غير صالحة"))
        text = f"{where}: {reason}" if where else reason
        if text in messages:  # collapse duplicates (e.g. union variants)
            continue
        messages.append(text)
        details.append(
            {
                "field": leaf,
                "label": _FIELD_LABELS.get(leaf, leaf),
                "index": index,
                "code": err.get("type", "value_error"),
                "message": reason,
            }
        )
    detail = "؛ ".join(messages) if messages else "البيانات المُدخلة غير صالحة."
    return detail, details


def register_error_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the application."""

    @app.exception_handler(RequestValidationError)
    async def _request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        detail, errors = _validation_errors(exc)
        return _problem(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation Error",
            detail,
            code="validation_error",
            errors=errors,
        )

    @app.exception_handler(RateLimitExceededError)
    async def _rate_limited(_: Request, exc: RateLimitExceededError) -> JSONResponse:
        return rate_limited_response(exc)

    @app.exception_handler(EntityNotFoundError)
    async def _not_found(_: Request, exc: EntityNotFoundError) -> JSONResponse:
        return _problem(status.HTTP_404_NOT_FOUND, "Not Found", str(exc), code=_error_code(exc))

    @app.exception_handler(BusinessRuleViolationError)
    async def _business_rule(_: Request, exc: BusinessRuleViolationError) -> JSONResponse:
        return _problem(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Business Rule Violation",
            str(exc),
            code=_error_code(exc),
        )

    @app.exception_handler(ConflictError)
    async def _conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return _problem(status.HTTP_409_CONFLICT, "Conflict", str(exc), code=_error_code(exc))

    @app.exception_handler(AuthenticationError)
    async def _unauthenticated(_: Request, exc: AuthenticationError) -> JSONResponse:
        return _problem(
            status.HTTP_401_UNAUTHORIZED, "Unauthorized", str(exc), code=_error_code(exc)
        )

    @app.exception_handler(AuthorizationError)
    async def _forbidden(_: Request, exc: AuthorizationError) -> JSONResponse:
        return _problem(status.HTTP_403_FORBIDDEN, "Forbidden", str(exc), code=_error_code(exc))

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return _problem(
            status.HTTP_400_BAD_REQUEST, "Domain Error", str(exc), code=_error_code(exc)
        )

    @app.exception_handler(ApplicationError)
    async def _application_error(_: Request, exc: ApplicationError) -> JSONResponse:
        return _problem(
            status.HTTP_400_BAD_REQUEST, "Application Error", str(exc), code=_error_code(exc)
        )
