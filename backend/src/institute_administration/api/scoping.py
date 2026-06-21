"""Request-scoped access control.

Resolves which halaqahs the current user may touch. Super admins are
unrestricted; a teacher is limited to the halaqahs they lead. Routers use this
to enforce "a teacher sees and edits only their own data".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from institute_administration.api.dependencies import DbSession
from institute_administration.modules.halaqahs.repository import SqlAlchemyHalaqahRepository
from institute_administration.modules.identity.dependencies import CurrentUser
from institute_administration.modules.identity.domain import UserRole
from institute_administration.modules.teachers.repository import SqlAlchemyTeacherRepository


@dataclass(frozen=True)
class AccessScope:
    """The data a request is allowed to reach."""

    is_admin: bool
    teacher_id: UUID | None
    # None means unrestricted (super admin); a set restricts to those halaqahs.
    halaqah_ids: frozenset[UUID] | None

    def allows_halaqah(self, halaqah_id: UUID | None) -> bool:
        if self.halaqah_ids is None:
            return True
        return halaqah_id is not None and halaqah_id in self.halaqah_ids


async def get_scope(current_user: CurrentUser, session: DbSession) -> AccessScope:
    if current_user.role == UserRole.SUPER_ADMIN:
        return AccessScope(is_admin=True, teacher_id=None, halaqah_ids=None)
    teacher = await SqlAlchemyTeacherRepository(session).get_view_by_user_id(current_user.id)
    if teacher is None:
        # An authenticated non-admin with no teacher profile sees nothing.
        return AccessScope(is_admin=False, teacher_id=None, halaqah_ids=frozenset())
    ids = await SqlAlchemyHalaqahRepository(session).ids_for_teacher(teacher.id)
    return AccessScope(is_admin=False, teacher_id=teacher.id, halaqah_ids=frozenset(ids))


ScopeDep = Annotated[AccessScope, Depends(get_scope)]
