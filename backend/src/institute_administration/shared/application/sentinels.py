"""A typed ``UNSET`` sentinel for partial-update (PATCH) inputs.

It distinguishes "field was not provided" from "field was explicitly set to
``None``", which a plain ``None`` default cannot express for nullable fields.
Using an ``Enum`` singleton makes the sentinel friendly to static type
narrowing: ``if value is not UNSET:`` narrows ``T | Unset`` down to ``T``.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal


class _Unset(Enum):
    UNSET = "UNSET"

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return "UNSET"


UNSET = _Unset.UNSET
type Unset = Literal[_Unset.UNSET]
