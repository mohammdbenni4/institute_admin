"""Problems domain layer: ProblemLevel and Problem aggregates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID, uuid4

from institute_administration.shared.application.pagination import Page
from institute_administration.shared.domain import (
    AggregateRoot,
    ConflictError,
    EntityNotFoundError,
)


class ProblemLevel(AggregateRoot[UUID]):
    """A category/severity level for problems (e.g. نطق, حفظ, سلوك)."""

    def __init__(
        self,
        *,
        id: UUID,
        name: str,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, *, name: str) -> ProblemLevel:
        return cls(id=uuid4(), name=name.strip())

    def rename(self, name: str) -> None:
        self.name = name.strip()


class Problem(AggregateRoot[UUID]):
    """A specific, named difficulty that can be tagged on a student's daily record."""

    def __init__(
        self,
        *,
        id: UUID,
        name: str,
        problem_level_id: UUID,
        level_name: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.problem_level_id = problem_level_id
        self.level_name = level_name
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, *, name: str, problem_level_id: UUID) -> Problem:
        return cls(id=uuid4(), name=name.strip(), problem_level_id=problem_level_id)

    def rename(self, name: str) -> None:
        self.name = name.strip()

    def change_level(self, level_id: UUID) -> None:
        self.problem_level_id = level_id


# ---------------------------------------------------------------------------
# Repository interfaces
# ---------------------------------------------------------------------------


class ProblemLevelRepository(ABC):
    @abstractmethod
    async def add(self, level: ProblemLevel) -> None: ...

    @abstractmethod
    async def update(self, level: ProblemLevel) -> None: ...

    @abstractmethod
    async def get_by_id(self, level_id: UUID) -> ProblemLevel | None: ...

    @abstractmethod
    async def exists_by_name(self, name: str, *, exclude_id: UUID | None = None) -> bool: ...

    @abstractmethod
    async def list(self, page: Page) -> list[ProblemLevel]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def delete(self, level: ProblemLevel) -> None: ...


class ProblemRepository(ABC):
    @abstractmethod
    async def add(self, problem: Problem) -> None: ...

    @abstractmethod
    async def update(self, problem: Problem) -> None: ...

    @abstractmethod
    async def get_by_id(self, problem_id: UUID) -> Problem | None: ...

    @abstractmethod
    async def get_by_ids(self, problem_ids: list[UUID]) -> list[Problem]: ...

    @abstractmethod
    async def exists_by_name_in_level(
        self,
        name: str,
        level_id: UUID,
        *,
        exclude_id: UUID | None = None,
    ) -> bool: ...

    @abstractmethod
    async def list(self, page: Page, *, level_id: UUID | None = None) -> list[Problem]: ...

    @abstractmethod
    async def count(self, *, level_id: UUID | None = None) -> int: ...

    @abstractmethod
    async def delete(self, problem: Problem) -> None: ...


# ---------------------------------------------------------------------------
# Domain errors
# ---------------------------------------------------------------------------


class ProblemLevelNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "مستوى الصعوبة غير موجود") -> None:
        super().__init__(message)


class ProblemLevelNameAlreadyExistsError(ConflictError):
    def __init__(self, message: str = "اسم مستوى الصعوبة مستخدم بالفعل") -> None:
        super().__init__(message)


class ProblemLevelInUseError(ConflictError):
    def __init__(self, message: str = "لا يمكن حذف مستوى يحتوي على صعوبات") -> None:
        super().__init__(message)


class ProblemNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "الصعوبة غير موجودة") -> None:
        super().__init__(message)


class ProblemNameAlreadyExistsInLevelError(ConflictError):
    def __init__(self, message: str = "اسم الصعوبة مستخدم بالفعل في هذا المستوى") -> None:
        super().__init__(message)
