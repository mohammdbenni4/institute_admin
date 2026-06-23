"""Problems infrastructure: SQLAlchemy repository implementations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.core.config import get_settings
from institute_administration.modules.problems.domain import (
    Problem,
    ProblemLevel,
    ProblemLevelRepository,
    ProblemRepository,
)
from institute_administration.modules.problems.models import ProblemLevelModel, ProblemModel
from institute_administration.shared.application.pagination import Page


def _level_to_entity(m: ProblemLevelModel) -> ProblemLevel:
    return ProblemLevel(
        id=m.id,
        name=m.name,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _problem_to_entity(m: ProblemModel, level_name: str | None = None) -> Problem:
    return Problem(
        id=m.id,
        name=m.name,
        problem_level_id=m.problem_level_id,
        level_name=level_name,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyProblemLevelRepository(ProblemLevelRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._collation = get_settings().arabic_collation

    async def add(self, level: ProblemLevel) -> None:
        self._session.add(ProblemLevelModel(id=level.id, name=level.name))
        await self._session.flush()

    async def update(self, level: ProblemLevel) -> None:
        model = await self._session.get(ProblemLevelModel, level.id)
        if model is None:
            return
        model.name = level.name
        await self._session.flush()

    async def get_by_id(self, level_id: UUID) -> ProblemLevel | None:
        model = await self._session.get(ProblemLevelModel, level_id)
        return _level_to_entity(model) if model else None

    async def exists_by_name(self, name: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(ProblemLevelModel.id).where(ProblemLevelModel.name == name.strip())
        if exclude_id is not None:
            stmt = stmt.where(ProblemLevelModel.id != exclude_id)
        result = await self._session.execute(stmt.limit(1))
        return result.first() is not None

    async def list(self, page: Page) -> list[ProblemLevel]:
        result = await self._session.execute(
            select(ProblemLevelModel)
            .order_by(ProblemLevelModel.name.collate(self._collation))
            .limit(page.limit)
            .offset(page.offset)
        )
        return [_level_to_entity(m) for m in result.scalars().all()]

    async def count(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(ProblemLevelModel)
        )
        return int(result.scalar_one())

    async def delete(self, level: ProblemLevel) -> None:
        model = await self._session.get(ProblemLevelModel, level.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()


class SqlAlchemyProblemRepository(ProblemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._collation = get_settings().arabic_collation

    async def add(self, problem: Problem) -> None:
        self._session.add(
            ProblemModel(
                id=problem.id,
                name=problem.name,
                problem_level_id=problem.problem_level_id,
            )
        )
        await self._session.flush()

    async def update(self, problem: Problem) -> None:
        model = await self._session.get(ProblemModel, problem.id)
        if model is None:
            return
        model.name = problem.name
        model.problem_level_id = problem.problem_level_id
        await self._session.flush()

    async def get_by_id(self, problem_id: UUID) -> Problem | None:
        result = await self._session.execute(
            select(ProblemModel, ProblemLevelModel.name)
            .join(ProblemLevelModel, ProblemModel.problem_level_id == ProblemLevelModel.id)
            .where(ProblemModel.id == problem_id)
        )
        row = result.first()
        if row is None:
            return None
        model, level_name = row
        return _problem_to_entity(model, level_name)

    async def get_by_ids(self, problem_ids: list[UUID]) -> list[Problem]:
        if not problem_ids:
            return []
        result = await self._session.execute(
            select(ProblemModel, ProblemLevelModel.name)
            .join(ProblemLevelModel, ProblemModel.problem_level_id == ProblemLevelModel.id)
            .where(ProblemModel.id.in_(problem_ids))
        )
        return [_problem_to_entity(m, lname) for m, lname in result.all()]

    async def exists_by_name_in_level(
        self,
        name: str,
        level_id: UUID,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        stmt = (
            select(ProblemModel.id)
            .where(ProblemModel.name == name.strip())
            .where(ProblemModel.problem_level_id == level_id)
        )
        if exclude_id is not None:
            stmt = stmt.where(ProblemModel.id != exclude_id)
        result = await self._session.execute(stmt.limit(1))
        return result.first() is not None

    async def list(self, page: Page, *, level_id: UUID | None = None) -> list[Problem]:
        stmt = (
            select(ProblemModel, ProblemLevelModel.name)
            .join(ProblemLevelModel, ProblemModel.problem_level_id == ProblemLevelModel.id)
        )
        if level_id is not None:
            stmt = stmt.where(ProblemModel.problem_level_id == level_id)
        stmt = (
            stmt.order_by(
                ProblemLevelModel.name.collate(self._collation),
                ProblemModel.name.collate(self._collation),
            )
            .limit(page.limit)
            .offset(page.offset)
        )
        result = await self._session.execute(stmt)
        return [_problem_to_entity(m, lname) for m, lname in result.all()]

    async def count(self, *, level_id: UUID | None = None) -> int:
        stmt = select(func.count()).select_from(ProblemModel)
        if level_id is not None:
            stmt = stmt.where(ProblemModel.problem_level_id == level_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def delete(self, problem: Problem) -> None:
        model = await self._session.get(ProblemModel, problem.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
