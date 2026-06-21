"""Shared pagination primitives used by query/list use cases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    """An offset/limit pagination request."""

    limit: int = 50
    offset: int = 0
