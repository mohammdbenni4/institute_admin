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

# Arabic labels for the request fields users actually fill in, so a malformed
# request explains *which* field and *why* — never a bare English validation dump.
_FIELD_LABELS: dict[str, str] = {
    "full_name": "الاسم الكامل",
    "email": "البريد الإلكتروني",
    "password": "كلمة المرور",
    "role": "الدور",
    "date_of_birth": "تاريخ الميلاد",
    "academic_study": "المؤهل الأكاديمي",
    "islamic_study": "المؤهل الشرعي",
    "is_assistant": "معلم مساعد",
    "is_active": "الحالة",
}

# Arabic templates keyed by Pydantic v2 error type. Anything unmapped falls back
# to the validator's own message so we never lose information.
_ERROR_TEMPLATES: dict[str, str] = {
    "missing": "هذا الحقل مطلوب",
    "string_too_short": "أقصر من الحد المسموح",
    "string_too_long": "أطول من الحد المسموح",
    "extra_forbidden": "حقل غير مسموح به",
    "value_error": "قيمة غير صالحة",
}


def _problem(status_code: int, title: str, detail: str) -> JSONResponse:
    """Return an RFC 9457-style problem response."""
    return JSONResponse(
        status_code=status_code,
        content={"title": title, "status": status_code, "detail": detail},
    )


def _field_name(loc: tuple[Any, ...]) -> str:
    """The user-facing field name from a Pydantic error location (drops 'body')."""
    parts = [str(p) for p in loc if p != "body"]
    return parts[-1] if parts else ""


def _validation_detail(exc: RequestValidationError) -> str:
    """Render Pydantic's structured errors as one readable Arabic sentence."""
    messages: list[str] = []
    for err in exc.errors():
        name = _field_name(err.get("loc", ()))
        label = _FIELD_LABELS.get(name, name)
        if name == "email":  # the email validator's own message is English
            reason = "بريد إلكتروني غير صالح"
        else:
            reason = _ERROR_TEMPLATES.get(err.get("type", ""), err.get("msg", "قيمة غير صالحة"))
        text = f"{label}: {reason}" if label else reason
        if text not in messages:  # collapse duplicates (e.g. union variants)
            messages.append(text)
    return "؛ ".join(messages) if messages else "البيانات المُدخلة غير صالحة."


def register_error_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the application."""

    @app.exception_handler(RequestValidationError)
    async def _request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation Error", _validation_detail(exc)
        )

    @app.exception_handler(EntityNotFoundError)
    async def _not_found(_: Request, exc: EntityNotFoundError) -> JSONResponse:
        return _problem(status.HTTP_404_NOT_FOUND, "Not Found", str(exc))

    @app.exception_handler(BusinessRuleViolationError)
    async def _business_rule(_: Request, exc: BusinessRuleViolationError) -> JSONResponse:
        return _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Business Rule Violation", str(exc))

    @app.exception_handler(ConflictError)
    async def _conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return _problem(status.HTTP_409_CONFLICT, "Conflict", str(exc))

    @app.exception_handler(AuthenticationError)
    async def _unauthenticated(_: Request, exc: AuthenticationError) -> JSONResponse:
        return _problem(status.HTTP_401_UNAUTHORIZED, "Unauthorized", str(exc))

    @app.exception_handler(AuthorizationError)
    async def _forbidden(_: Request, exc: AuthorizationError) -> JSONResponse:
        return _problem(status.HTTP_403_FORBIDDEN, "Forbidden", str(exc))

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return _problem(status.HTTP_400_BAD_REQUEST, "Domain Error", str(exc))

    @app.exception_handler(ApplicationError)
    async def _application_error(_: Request, exc: ApplicationError) -> JSONResponse:
        return _problem(status.HTTP_400_BAD_REQUEST, "Application Error", str(exc))
