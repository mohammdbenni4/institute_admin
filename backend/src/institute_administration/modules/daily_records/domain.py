"""Daily records domain layer.

A :class:`DailyRecord` is the daily assessment of one student in a halaqah,
recorded by a teacher. It references the student, teacher and halaqah by id only.

The reward-card scores (``card_present``, ``card_exam``, ``card_attitude``) and
their sum (``total_points``) are *derived* values: they are computed from the
attendance/rating/attitude inputs rather than supplied by the client, so they
can never drift out of sync with the data they summarise. They are exposed as
read-only properties here and persisted as denormalised columns purely so the
database can sort and aggregate on them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid4

from institute_administration.shared.application.pagination import Page
from institute_administration.shared.domain import (
    AggregateRoot,
    BusinessRuleViolationError,
    ConflictError,
    EntityNotFoundError,
)

RATING_MIN, RATING_MAX = 1, 4
ATTITUDE_MIN, ATTITUDE_MAX = 1, 3


@dataclass(frozen=True)
class ScoringPolicy:
    """Reward-card weights. Institute-configurable (see the ``scoring`` module).

    A record's ``card_*`` columns are a snapshot of the policy in force when it
    was written, so changing the policy never silently rewrites history.
    """

    present_points: int
    rating_points: dict[int, int]  # examination rating (1-4) -> card points
    attitude_points: dict[int, int]  # behaviour rating (1-3) -> card points

    def card_present(self, present: bool) -> int:
        return self.present_points if present else 0

    def card_exam(self, rating: int | None) -> int:
        return self.rating_points.get(rating, 0) if rating is not None else 0

    def card_attitude(self, attitude: int | None) -> int:
        return self.attitude_points.get(attitude, 0) if attitude is not None else 0

    def apply(self, record: DailyRecord) -> None:
        """Recompute and store the four card scores on ``record``."""
        record.card_present = self.card_present(record.present)
        record.card_exam = self.card_exam(record.rating)
        record.card_attitude = self.card_attitude(record.attitude)
        record.total_points = (
            record.card_present + record.card_exam + record.card_attitude + record.added_points
        )


DEFAULT_SCORING = ScoringPolicy(
    present_points=5,
    rating_points={4: 7, 3: 5, 2: 3, 1: 0},
    attitude_points={3: 3, 2: 2, 1: 1},
)
"""The built-in weights (present=5; rating 4/3/2→7/5/3; attitude = its value)."""


class DailyRecord(AggregateRoot[UUID]):
    """One student's assessment for a single day."""

    def __init__(
        self,
        *,
        id: UUID,
        student_id: UUID,
        teacher_id: UUID,
        halaqah_id: UUID,
        record_date: date,
        present: bool,
        exam_from: int | None = None,
        exam_to: int | None = None,
        exam_total: int | None = None,
        homework: str | None = None,
        problems: str | None = None,
        rating: int | None = None,
        revision_lesson: str | None = None,
        revision_rating: int | None = None,
        attitude: int | None = None,
        added_points: int = 0,
        notes: str | None = None,
        card_present: int | None = None,
        card_exam: int | None = None,
        card_attitude: int | None = None,
        total_points: int | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.student_id = student_id
        self.teacher_id = teacher_id
        self.halaqah_id = halaqah_id
        self.record_date = record_date
        self.present = present
        self.exam_from = exam_from
        self.exam_to = exam_to
        self.exam_total = exam_total
        self.homework = homework
        self.problems = problems
        self.rating = rating
        self.revision_lesson = revision_lesson
        self.revision_rating = revision_rating
        self.attitude = attitude
        self.added_points = added_points
        self.notes = notes
        self.created_at = created_at
        self.updated_at = updated_at
        self._validate()
        # Card scores are a stored snapshot: reuse persisted values when loading
        # from the database, otherwise compute with the built-in default policy
        # (the application layer re-applies the institute's configured policy).
        self.card_present = 0
        self.card_exam = 0
        self.card_attitude = 0
        self.total_points = 0
        if card_present is None:
            DEFAULT_SCORING.apply(self)
        else:
            self.card_present = card_present
            self.card_exam = card_exam or 0
            self.card_attitude = card_attitude or 0
            self.total_points = total_points or 0

    @classmethod
    def create(
        cls,
        *,
        student_id: UUID,
        teacher_id: UUID,
        halaqah_id: UUID,
        record_date: date,
        present: bool,
        exam_from: int | None = None,
        exam_to: int | None = None,
        exam_total: int | None = None,
        homework: str | None = None,
        problems: str | None = None,
        rating: int | None = None,
        revision_lesson: str | None = None,
        revision_rating: int | None = None,
        attitude: int | None = None,
        added_points: int = 0,
        notes: str | None = None,
    ) -> DailyRecord:
        return cls(
            id=uuid4(),
            student_id=student_id,
            teacher_id=teacher_id,
            halaqah_id=halaqah_id,
            record_date=record_date,
            present=present,
            exam_from=exam_from,
            exam_to=exam_to,
            exam_total=exam_total,
            homework=homework,
            problems=problems,
            rating=rating,
            revision_lesson=revision_lesson,
            revision_rating=revision_rating,
            attitude=attitude,
            added_points=added_points,
            notes=notes,
        )

    # --- Reward-card scores --------------------------------------------------

    def apply_scoring(self, policy: ScoringPolicy) -> None:
        """Recompute the card scores from a (possibly configured) policy."""
        policy.apply(self)

    # --- Invariants ----------------------------------------------------------

    def revalidate(self) -> None:
        """Re-check invariants after the application layer mutates fields."""
        self._validate()

    def _validate(self) -> None:
        if self.rating is not None and not RATING_MIN <= self.rating <= RATING_MAX:
            raise InvalidRatingError
        if (
            self.revision_rating is not None
            and not RATING_MIN <= self.revision_rating <= RATING_MAX
        ):
            raise InvalidRatingError
        if self.attitude is not None and not ATTITUDE_MIN <= self.attitude <= ATTITUDE_MAX:
            raise InvalidAttitudeError
        for value in (self.exam_from, self.exam_to, self.exam_total):
            if value is not None and value < 0:
                raise InvalidExamRangeError("قيم الاختبار يجب ألا تكون سالبة")
        if (
            self.exam_from is not None
            and self.exam_to is not None
            and self.exam_to < self.exam_from
        ):
            raise InvalidExamRangeError
        if self.added_points < 0:
            raise InvalidAddedPointsError


class DailyRecordRepository(ABC):
    @abstractmethod
    async def add(self, record: DailyRecord) -> None: ...

    @abstractmethod
    async def update(self, record: DailyRecord) -> None: ...

    @abstractmethod
    async def get_by_id(self, record_id: UUID) -> DailyRecord | None: ...

    @abstractmethod
    async def list(
        self,
        page: Page,
        *,
        student_id: UUID | None = None,
        teacher_id: UUID | None = None,
        halaqah_id: UUID | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
        record_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[DailyRecord]: ...

    @abstractmethod
    async def count(
        self,
        *,
        student_id: UUID | None = None,
        teacher_id: UUID | None = None,
        halaqah_id: UUID | None = None,
        halaqah_ids: frozenset[UUID] | None = None,
        record_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int: ...

    @abstractmethod
    async def delete(self, record: DailyRecord) -> None: ...


class DailyRecordNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "السجل اليومي غير موجود") -> None:
        super().__init__(message)


class DuplicateDailyRecordError(ConflictError):
    def __init__(self, message: str = "يوجد سجل يومي لهذا الطالب في هذا التاريخ بالفعل") -> None:
        super().__init__(message)


class InvalidStudentError(ConflictError):
    def __init__(self, message: str = "الطالب المحدد غير موجود") -> None:
        super().__init__(message)


class InvalidTeacherError(ConflictError):
    def __init__(self, message: str = "المعلم المحدد غير موجود") -> None:
        super().__init__(message)


class InvalidHalaqahError(ConflictError):
    def __init__(self, message: str = "الحلقة المحددة غير موجودة") -> None:
        super().__init__(message)


class InvalidRatingError(BusinessRuleViolationError):
    def __init__(self, message: str = "التقييم يجب أن يكون بين 1 و 4") -> None:
        super().__init__(message)


class InvalidAttitudeError(BusinessRuleViolationError):
    def __init__(self, message: str = "تقييم السلوك يجب أن يكون بين 1 و 3") -> None:
        super().__init__(message)


class InvalidExamRangeError(BusinessRuleViolationError):
    def __init__(self, message: str = "نهاية الاختبار يجب ألا تسبق بدايته") -> None:
        super().__init__(message)


class InvalidAddedPointsError(BusinessRuleViolationError):
    def __init__(self, message: str = "النقاط المضافة يجب ألا تكون سالبة") -> None:
        super().__init__(message)
