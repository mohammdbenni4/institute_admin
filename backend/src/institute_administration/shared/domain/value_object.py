"""Base class for value objects.

A value object is immutable and has no identity: two value objects are equal
when all of their attributes are equal. Subclass as a frozen dataclass::

    @dataclass(frozen=True, slots=True)
    class SurahNumber(ValueObject):
        value: int

        def __post_init__(self) -> None:
            if not 1 <= self.value <= 114:
                raise BusinessRuleViolationError("Surah number must be between 1 and 114")
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValueObject:
    """Immutable, attribute-based-equality building block."""
