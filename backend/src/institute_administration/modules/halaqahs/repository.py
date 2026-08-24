"""Halaqahs infrastructure: SQLAlchemy repository implementation.

The view queries join the teacher (via its user) and the halaqah type for their
display names, and compute the live student count with a correlated subquery.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Select, delete, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from institute_administration.core.config import get_settings
from institute_administration.modules.halaqah_types.models import HalaqahTypeModel
from institute_administration.modules.halaqahs.domain import (
    Halaqah,
    HalaqahRepository,
    HalaqahView,
    InvalidHalaqahRelationError,
    InvalidHalaqahTeacherError,
    TeacherBrief,
)
from institute_administration.modules.halaqahs.models import HalaqahModel, HalaqahTeacherModel
from institute_administration.modules.identity.models import UserModel
from institute_administration.modules.students.models import StudentModel
from institute_administration.modules.teachers.models import TeacherModel
from institute_administration.modules.times.models import TimeModel
from institute_administration.shared.application.pagination import Page

_student_count = (
    select(func.count(StudentModel.id))
    .where(StudentModel.halaqah_id == HalaqahModel.id)
    .correlate(HalaqahModel)
    .scalar_subquery()
)


def _is_member(teacher_id: UUID) -> Any:
    """SQL predicate: this halaqah has the given teacher among its members."""
    return exists().where(
        HalaqahTeacherModel.halaqah_id == HalaqahModel.id,
        HalaqahTeacherModel.teacher_id == teacher_id,
    )


def _entity(model: HalaqahModel) -> Halaqah:
    return Halaqah(
        id=model.id,
        name=model.name,
        teacher_id=model.teacher_id,
        halaqah_type_id=model.halaqah_type_id,
        level=model.level,
        age=model.age,
        time_id=model.time_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _schedule(time_model: TimeModel | None) -> dict[str, dict[str, str]]:
    """Only the days that actually have a session, as ``{"from", "to"}`` pairs."""
    if time_model is None:
        return {}
    return {day: value for day, value in time_model.day_values().items() if value}


def _view(
    model: HalaqahModel,
    teacher_name: str,
    type_name: str,
    count: int,
    time_model: TimeModel | None = None,
    teachers: tuple[TeacherBrief, ...] = (),
) -> HalaqahView:
    return HalaqahView(
        id=model.id,
        name=model.name,
        level=model.level,
        age=model.age,
        teacher_id=model.teacher_id,
        teacher_name=teacher_name,
        # Fall back to the responsible teacher alone: a halaqah always has at least
        # them, and a view built before membership was loaded must not look empty.
        teachers=teachers or (TeacherBrief(id=model.teacher_id, name=teacher_name),),
        halaqah_type_id=model.halaqah_type_id,
        halaqah_type_name=type_name,
        time_id=model.time_id,
        time_name=time_model.name if time_model else None,
        schedule=_schedule(time_model),
        number_of_students=count,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyHalaqahRepository(HalaqahRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_collation = get_settings().arabic_collation

    def _view_select(self) -> Select[tuple[HalaqahModel, str, str, int, TimeModel | None]]:
        return (
            select(
                HalaqahModel,
                UserModel.full_name,
                HalaqahTypeModel.name,
                _student_count.label("number_of_students"),
                TimeModel,
            )
            .join(TeacherModel, HalaqahModel.teacher_id == TeacherModel.id)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .join(HalaqahTypeModel, HalaqahModel.halaqah_type_id == HalaqahTypeModel.id)
            .outerjoin(TimeModel, HalaqahModel.time_id == TimeModel.id)
        )

    async def _load_teachers(
        self, halaqah_ids: Sequence[UUID]
    ) -> dict[UUID, tuple[TeacherBrief, ...]]:
        """Membership for a page of halaqahs in one query, responsible teacher first."""
        if not halaqah_ids:
            return {}
        result = await self._session.execute(
            select(
                HalaqahTeacherModel.halaqah_id,
                TeacherModel.id,
                UserModel.full_name,
                HalaqahModel.teacher_id,
            )
            .join(TeacherModel, HalaqahTeacherModel.teacher_id == TeacherModel.id)
            .join(UserModel, TeacherModel.user_id == UserModel.id)
            .join(HalaqahModel, HalaqahTeacherModel.halaqah_id == HalaqahModel.id)
            .where(HalaqahTeacherModel.halaqah_id.in_(halaqah_ids))
            .order_by(UserModel.full_name.collate(self._order_collation))
        )
        grouped: dict[UUID, list[tuple[bool, TeacherBrief]]] = {}
        for halaqah_id, teacher_id, name, responsible_id in result.all():
            grouped.setdefault(halaqah_id, []).append(
                (teacher_id == responsible_id, TeacherBrief(id=teacher_id, name=name))
            )
        # Responsible first, then the rest alphabetically (already ordered by the query).
        return {
            hid: tuple(brief for _, brief in sorted(rows, key=lambda r: not r[0]))
            for hid, rows in grouped.items()
        }

    async def _sync_membership(self, halaqah_id: UUID, responsible_id: UUID) -> None:
        """Guarantee the responsible teacher is a member.

        Called after every create and update: changing a halaqah's responsible
        teacher must grant that teacher access, or an admin could reassign a halaqah
        to someone who then cannot open it.
        """
        exists = await self._session.execute(
            select(HalaqahTeacherModel.teacher_id).where(
                HalaqahTeacherModel.halaqah_id == halaqah_id,
                HalaqahTeacherModel.teacher_id == responsible_id,
            )
        )
        if exists.scalar_one_or_none() is None:
            self._session.add(HalaqahTeacherModel(halaqah_id=halaqah_id, teacher_id=responsible_id))
            await self._session.flush()

    async def set_teachers(self, halaqah_id: UUID, teacher_ids: Sequence[UUID]) -> None:
        model = await self._session.get(HalaqahModel, halaqah_id)
        if model is None:  # pragma: no cover - guarded by the service layer
            return
        # The responsible teacher is not removable through this path — dropping them
        # would leave the halaqah's printed report naming someone with no access.
        wanted = {model.teacher_id, *teacher_ids}
        current = set(
            (
                await self._session.execute(
                    select(HalaqahTeacherModel.teacher_id).where(
                        HalaqahTeacherModel.halaqah_id == halaqah_id
                    )
                )
            )
            .scalars()
            .all()
        )
        for teacher_id in current - wanted:
            await self._session.execute(
                delete(HalaqahTeacherModel).where(
                    HalaqahTeacherModel.halaqah_id == halaqah_id,
                    HalaqahTeacherModel.teacher_id == teacher_id,
                )
            )
        for teacher_id in wanted - current:
            self._session.add(HalaqahTeacherModel(halaqah_id=halaqah_id, teacher_id=teacher_id))
        try:
            await self._session.flush()
        except IntegrityError as exc:  # a teacher_id that does not exist
            raise InvalidHalaqahTeacherError from exc

    async def add(self, halaqah: Halaqah) -> None:
        self._session.add(
            HalaqahModel(
                id=halaqah.id,
                name=halaqah.name,
                teacher_id=halaqah.teacher_id,
                halaqah_type_id=halaqah.halaqah_type_id,
                level=halaqah.level,
                age=halaqah.age,
                time_id=halaqah.time_id,
            )
        )
        await self._flush()
        await self._sync_membership(halaqah.id, halaqah.teacher_id)

    async def update(self, halaqah: Halaqah) -> None:
        model = await self._session.get(HalaqahModel, halaqah.id)
        if model is None:  # pragma: no cover - guarded by the service layer
            return
        model.name = halaqah.name
        model.teacher_id = halaqah.teacher_id
        model.halaqah_type_id = halaqah.halaqah_type_id
        model.level = halaqah.level
        model.age = halaqah.age
        model.time_id = halaqah.time_id
        await self._flush()
        await self._sync_membership(halaqah.id, halaqah.teacher_id)

    async def get_entity(self, halaqah_id: UUID) -> Halaqah | None:
        model = await self._session.get(HalaqahModel, halaqah_id)
        return _entity(model) if model else None

    async def get_view(self, halaqah_id: UUID) -> HalaqahView | None:
        result = await self._session.execute(
            self._view_select().where(HalaqahModel.id == halaqah_id)
        )
        row = result.first()
        if row is None:
            return None
        teachers = await self._load_teachers([halaqah_id])
        return _view(row[0], row[1], row[2], row[3], row[4], teachers.get(halaqah_id, ()))

    async def list_views(self, page: Page, *, teacher_id: UUID | None = None) -> list[HalaqahView]:
        stmt = self._view_select()
        if teacher_id is not None:
            # Membership, not responsibility: a teacher assigned to a halaqah they do
            # not lead must still find it in their list.
            stmt = stmt.where(_is_member(teacher_id))
        result = await self._session.execute(
            stmt.order_by(HalaqahModel.name.collate(self._order_collation))
            .limit(page.limit)
            .offset(page.offset)
        )
        rows = result.all()
        teachers = await self._load_teachers([row[0].id for row in rows])
        return [
            _view(row[0], row[1], row[2], row[3], row[4], teachers.get(row[0].id, ()))
            for row in rows
        ]

    async def count(self, *, teacher_id: UUID | None = None) -> int:
        stmt = select(func.count()).select_from(HalaqahModel)
        if teacher_id is not None:
            stmt = stmt.where(_is_member(teacher_id))
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def ids_for_teacher(self, teacher_id: UUID) -> set[UUID]:
        """The single source of truth for what a teacher may reach.

        Every scoped endpoint in the app — students, daily records, analytics,
        parent summons, upcoming exams — filters on the set this returns, so
        reading it from the membership table is the whole of the many-to-many
        change as far as access control is concerned.
        """
        result = await self._session.execute(
            select(HalaqahTeacherModel.halaqah_id).where(
                HalaqahTeacherModel.teacher_id == teacher_id
            )
        )
        return set(result.scalars().all())

    async def delete(self, halaqah: Halaqah) -> None:
        model = await self._session.get(HalaqahModel, halaqah.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def _flush(self) -> None:
        try:
            await self._session.flush()
        except IntegrityError as exc:  # bad teacher_id / halaqah_type_id / time_id
            raise InvalidHalaqahRelationError from exc
