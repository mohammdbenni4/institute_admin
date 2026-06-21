"""Translation of domain/application errors into HTTP responses.

Keeping this mapping in one place means the domain and application layers stay
free of any HTTP concerns: they raise meaningful exceptions, and this module
decides how each maps onto the transport.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
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


def _problem(status_code: int, title: str, detail: str) -> JSONResponse:
    """Return an RFC 9457-style problem response."""
    return JSONResponse(
        status_code=status_code,
        content={"title": title, "status": status_code, "detail": detail},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the application."""

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
