"""Base class for domain entities.

An entity has a stable identity that distinguishes it from other entities even
when its attributes change. Equality is therefore based on identity, not on the
values of its fields.
"""

from __future__ import annotations


class Entity[EntityIdT]:
    """An object defined by a continuous identity rather than its attributes.

    Intended as a base class; subclasses represent concrete domain entities.
    """

    def __init__(self, entity_id: EntityIdT) -> None:
        self._id = entity_id

    @property
    def id(self) -> EntityIdT:
        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash((type(self), self._id))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self._id!r})"
