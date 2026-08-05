"""Upcoming exams domain layer."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from institute_administration.shared.domain import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)

PART_MIN, PART_MAX = 1, 30


class ExamStatus(StrEnum):
    PENDING = "pending"  # مجدول
    DONE = "done"  # تم
    CANCELLED = "cancelled"  # ألغي


STATUS_LABELS: dict[ExamStatus, str] = {
    ExamStatus.PENDING: "مجدول",
    ExamStatus.DONE: "تم",
    ExamStatus.CANCELLED: "ألغي",
}


class UpcomingExamNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "الاختبار القادم غير موجود") -> None:
        super().__init__(message)


class InvalidExamPartError(BusinessRuleViolationError):
    def __init__(self, message: str = "رقم الجزء يجب أن يكون بين 1 و 30") -> None:
        super().__init__(message)


class InvalidExamRangeError(BusinessRuleViolationError):
    def __init__(self, message: str = "نطاق الاختبار غير صحيح") -> None:
        super().__init__(message)


class UpcomingExamView:
    """Read model: a planned exam plus the names both panels display."""

    def __init__(
        self,
        *,
        id: UUID,
        student_id: UUID,
        student_name: str,
        teacher_id: UUID,
        teacher_name: str,
        halaqah_id: UUID,
        halaqah_name: str,
        scheduled_date: date,
        part: int | None,
        exam_from: int | None,
        exam_to: int | None,
        notes: str | None,
        status: ExamStatus,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.id = id
        self.student_id = student_id
        self.student_name = student_name
        self.teacher_id = teacher_id
        self.teacher_name = teacher_name
        self.halaqah_id = halaqah_id
        self.halaqah_name = halaqah_name
        self.scheduled_date = scheduled_date
        self.part = part
        self.exam_from = exam_from
        self.exam_to = exam_to
        self.notes = notes
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def status_label(self) -> str:
        return STATUS_LABELS[self.status]

    @property
    def summary(self) -> str:
        """Short Arabic description of what the exam covers, for a card."""
        bits: list[str] = []
        if self.part is not None:
            bits.append(f"الجزء {self.part}")
        if self.exam_from is not None and self.exam_to is not None:
            bits.append(f"من {self.exam_from} إلى {self.exam_to}")
        elif self.exam_to is not None:
            bits.append(f"إلى {self.exam_to}")
        elif self.exam_from is not None:
            bits.append(f"من {self.exam_from}")
        return " · ".join(bits) or "غير محدد"


def validate_parameters(part: int | None, exam_from: int | None, exam_to: int | None) -> None:
    """Guard the exam's coverage before it is stored."""
    if part is not None and not PART_MIN <= part <= PART_MAX:
        raise InvalidExamPartError
    for value in (exam_from, exam_to):
        if value is not None and value < 0:
            raise InvalidExamRangeError("قيم الاختبار يجب ألا تكون سالبة")
    if exam_from is not None and exam_to is not None and exam_to < exam_from:
        raise InvalidExamRangeError
