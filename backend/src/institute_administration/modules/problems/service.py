"""Problems application layer: use cases for problem levels and problems."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from institute_administration.modules.problems.domain import (
    Problem,
    ProblemLevel,
    ProblemLevelInUseError,
    ProblemLevelNameAlreadyExistsError,
    ProblemLevelNotFoundError,
    ProblemLevelRepository,
    ProblemNameAlreadyExistsInLevelError,
    ProblemNotFoundError,
    ProblemRepository,
)
from institute_administration.shared.application.pagination import Page
from institute_administration.shared.application.sentinels import UNSET, Unset

# ---------------------------------------------------------------------------
# ProblemLevel service
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CreateProblemLevelInput:
    name: str


@dataclass(frozen=True)
class UpdateProblemLevelInput:
    name: str | Unset = UNSET


class ProblemLevelService:
    def __init__(
        self,
        levels: ProblemLevelRepository,
        problems: ProblemRepository,
    ) -> None:
        self._levels = levels
        self._problems = problems

    async def create(self, data: CreateProblemLevelInput) -> ProblemLevel:
        if await self._levels.exists_by_name(data.name):
            raise ProblemLevelNameAlreadyExistsError
        level = ProblemLevel.create(name=data.name)
        await self._levels.add(level)
        return (await self._levels.get_by_id(level.id))  # type: ignore[return-value]

    async def get(self, level_id: UUID) -> ProblemLevel:
        level = await self._levels.get_by_id(level_id)
        if level is None:
            raise ProblemLevelNotFoundError
        return level

    async def list(self, page: Page) -> tuple[list[ProblemLevel], int]:
        return await self._levels.list(page), await self._levels.count()

    async def update(self, level_id: UUID, data: UpdateProblemLevelInput) -> ProblemLevel:
        level = await self.get(level_id)
        if data.name is not UNSET:
            if await self._levels.exists_by_name(data.name, exclude_id=level_id):
                raise ProblemLevelNameAlreadyExistsError
            level.rename(data.name)
        await self._levels.update(level)
        return await self.get(level_id)

    async def delete(self, level_id: UUID) -> None:
        level = await self.get(level_id)
        if await self._problems.count(level_id=level_id) > 0:
            raise ProblemLevelInUseError
        await self._levels.delete(level)


# ---------------------------------------------------------------------------
# Problem service
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CreateProblemInput:
    name: str
    level_id: UUID


@dataclass(frozen=True)
class UpdateProblemInput:
    name: str | Unset = UNSET
    level_id: UUID | Unset = UNSET


class ProblemService:
    def __init__(
        self,
        problems: ProblemRepository,
        levels: ProblemLevelRepository,
    ) -> None:
        self._problems = problems
        self._levels = levels

    async def create(self, data: CreateProblemInput) -> Problem:
        level = await self._levels.get_by_id(data.level_id)
        if level is None:
            raise ProblemLevelNotFoundError
        if await self._problems.exists_by_name_in_level(data.name, data.level_id):
            raise ProblemNameAlreadyExistsInLevelError
        problem = Problem.create(name=data.name, problem_level_id=data.level_id)
        await self._problems.add(problem)
        result = await self._problems.get_by_id(problem.id)
        return result  # type: ignore[return-value]

    async def get(self, problem_id: UUID) -> Problem:
        problem = await self._problems.get_by_id(problem_id)
        if problem is None:
            raise ProblemNotFoundError
        return problem

    async def get_by_ids(self, problem_ids: list[UUID]) -> list[Problem]:
        return await self._problems.get_by_ids(problem_ids)

    async def list(
        self, page: Page, *, level_id: UUID | None = None
    ) -> tuple[list[Problem], int]:
        return (
            await self._problems.list(page, level_id=level_id),
            await self._problems.count(level_id=level_id),
        )

    async def update(self, problem_id: UUID, data: UpdateProblemInput) -> Problem:
        problem = await self.get(problem_id)
        new_level_id = problem.problem_level_id
        if data.level_id is not UNSET:
            if await self._levels.get_by_id(data.level_id) is None:
                raise ProblemLevelNotFoundError
            new_level_id = data.level_id
            problem.change_level(data.level_id)
        if data.name is not UNSET:
            if await self._problems.exists_by_name_in_level(
                data.name, new_level_id, exclude_id=problem_id
            ):
                raise ProblemNameAlreadyExistsInLevelError
            problem.rename(data.name)
        await self._problems.update(problem)
        return await self.get(problem_id)

    async def delete(self, problem_id: UUID) -> None:
        problem = await self.get(problem_id)
        await self._problems.delete(problem)
