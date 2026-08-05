"""Request rate limiting.

Login is the endpoint that actually needs protecting: without a limit, a public
VPS invites unlimited password guessing against known accounts. The general limit
is a much looser backstop against a runaway client, and is deliberately generous
because the teacher app legitimately bursts (a whole halaqah's outbox draining in
one go).

State is per process and in memory. That is the right trade-off here — the API
runs as a single uvicorn process, there is no Redis to depend on, and a limiter
that resets on deploy is far better than none. If the deployment ever grows to
multiple workers this must move to a shared store, or each worker will allow the
full quota independently.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Request, status
from fastapi.responses import JSONResponse

from institute_administration.shared.application.exceptions import ApplicationError


class RateLimitExceededError(ApplicationError):
    """Too many requests from one caller in the configured window."""

    def __init__(self, retry_after: int) -> None:
        minutes = max(1, round(retry_after / 60))
        super().__init__(f"محاولات كثيرة جداً. يرجى المحاولة بعد {minutes} دقيقة.")
        self.retry_after = retry_after


@dataclass(frozen=True)
class Rule:
    """`limit` requests allowed per `window` seconds."""

    limit: int
    window: int


# Strict: a human typing their own password never needs more than this.
LOGIN = Rule(limit=8, window=300)
# Token refresh is automatic, so allow more, but not unbounded.
REFRESH = Rule(limit=60, window=300)
# Backstop for everything else, sized so a full outbox drain never trips it.
GENERAL = Rule(limit=600, window=60)


class SlidingWindowLimiter:
    """Counts hits per key inside a moving time window."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, rule: Rule) -> None:
        """Record a hit, or raise if the caller is over the limit."""
        now = time.monotonic()
        cutoff = now - rule.window
        hits = self._hits[key]
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= rule.limit:
            raise RateLimitExceededError(retry_after=int(hits[0] + rule.window - now) + 1)
        hits.append(now)

    def reset(self, key: str) -> None:
        """Forget a caller's history — used after a *successful* login so an honest
        user who mistyped a few times is not left locked out."""
        self._hits.pop(key, None)

    def prune(self, older_than: float = 3600.0) -> None:
        """Drop keys with no recent activity so the map cannot grow forever."""
        cutoff = time.monotonic() - older_than
        for key in [k for k, hits in self._hits.items() if not hits or hits[-1] <= cutoff]:
            del self._hits[key]


limiter = SlidingWindowLimiter()


def client_key(request: Request, suffix: str = "") -> str:
    """Identify the caller.

    Behind nginx the socket address is the proxy, so the first hop of
    `X-Forwarded-For` is the real client. It is spoofable by anyone talking to the
    API directly, which is acceptable for throttling but must never be used for
    authorisation.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "unknown")
    )
    return f"{ip}:{suffix}" if suffix else ip


def rate_limited_response(exc: RateLimitExceededError) -> JSONResponse:
    """A 429 in the same problem shape as every other error, message in Arabic."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "title": "Too Many Requests",
            "status": status.HTTP_429_TOO_MANY_REQUESTS,
            "detail": str(exc),
            "code": "rate_limit_exceeded",
        },
        headers={"Retry-After": str(exc.retry_after)},
    )


def login_throttle(request: Request) -> None:
    """Dependency for the login route: strict, and keyed per IP."""
    limiter.check(client_key(request, "login"), LOGIN)


def refresh_throttle(request: Request) -> None:
    """Dependency for token refresh: looser, since the app renews on its own."""
    limiter.check(client_key(request, "refresh"), REFRESH)
