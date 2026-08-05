"""Parent summons domain layer: the request lifecycle."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from institute_administration.shared.domain import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)


class SummonStatus(StrEnum):
    """Where a request has got to.

    The administration moves a request forward; it never goes backwards on its
    own, but an admin may correct a mistake by setting any status explicitly.
    """

    NEW = "new"  # قيد الانتظار
    REVIEWING = "reviewing"  # تتم المراجعة
    COMPLETED = "completed"  # منتهي


# The single source of truth for the wording: both apps render `status_label`
# straight from the response rather than keeping their own copy.
STATUS_LABELS: dict[SummonStatus, str] = {
    SummonStatus.NEW: "قيد الانتظار",
    SummonStatus.REVIEWING: "تتم المراجعة",
    SummonStatus.COMPLETED: "منتهي",
}


class ParentSummonNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "طلب الاستدعاء غير موجود") -> None:
        super().__init__(message)


class MissingSummonReasonError(BusinessRuleViolationError):
    def __init__(self, message: str = "يجب كتابة سبب الاستدعاء") -> None:
        super().__init__(message)


class ParentSummonView:
    """Read model: a request with every name the admin table needs to link to.

    The names are resolved once by the repository so the admin panel can render
    clickable teacher/student/halaqah links and a WhatsApp button without a
    request per row.
    """

    def __init__(
        self,
        *,
        id: UUID,
        student_id: UUID,
        student_name: str,
        father_name: str | None,
        father_number: str | None,
        teacher_id: UUID,
        teacher_name: str,
        halaqah_id: UUID,
        halaqah_name: str,
        reason: str,
        status: SummonStatus,
        admin_response: str | None,
        handled_at: datetime | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.id = id
        self.student_id = student_id
        self.student_name = student_name
        self.father_name = father_name
        self.father_number = father_number
        self.teacher_id = teacher_id
        self.teacher_name = teacher_name
        self.halaqah_id = halaqah_id
        self.halaqah_name = halaqah_name
        self.reason = reason
        self.status = status
        self.admin_response = admin_response
        self.handled_at = handled_at
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def status_label(self) -> str:
        return STATUS_LABELS[self.status]
