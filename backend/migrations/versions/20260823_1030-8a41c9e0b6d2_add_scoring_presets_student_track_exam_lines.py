"""Add scoring presets, the student track, and رشيدي line numbers.

Strictly additive — every change is a new table, a new nullable column, or a
CHECK that only constrains those new columns. No existing row is read, rewritten
or revalidated, so this runs against the live database without touching a single
byte of production data:

* ``scoring_presets`` is a brand-new table.
* ``students.student_type`` and ``students.scoring_preset_id`` are nullable with
  no server default, so existing students get NULL — which readers already treat
  as "قرآن, priced by the institute-wide settings", i.e. exactly today's behaviour.
* ``daily_records.exam_from_line``/``exam_to_line`` are nullable; all 5000+
  existing records get NULL, and the accompanying CHECKs are satisfied by NULL,
  so Postgres validates them instantly without a table scan of real values.

Revision ID: 8a41c9e0b6d2
Revises: 54d2f535295b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "8a41c9e0b6d2"
down_revision: str | None = "54d2f535295b"
branch_labels: str | None = None
depends_on: str | None = None


# Mirrors ScoringSettingsModel's defaults so a preset created straight from SQL is
# never half-populated. (name, default)
_WEIGHTS: list[tuple[str, int]] = [
    ("present_points", 5),
    ("rating_4_points", 7),
    ("rating_3_points", 5),
    ("rating_2_points", 3),
    ("rating_1_points", 0),
    ("revision_4_points", 7),
    ("revision_3_points", 5),
    ("revision_2_points", 3),
    ("revision_1_points", 0),
    ("attitude_3_points", 3),
    ("attitude_2_points", 2),
    ("attitude_1_points", 1),
    ("absent_points", 0),
    ("excused_points", 0),
    ("late_points", 5),
]

STUDENT_TYPE_ENUM = "student_type"


def upgrade() -> None:
    op.create_table(
        "scoring_presets",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        *[
            sa.Column(name, sa.SmallInteger(), nullable=False, server_default=str(default))
            for name, default in _WEIGHTS
        ],
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_scoring_presets_name"),
    )

    # `create_type=False` + an explicit CREATE TYPE keeps the enum's creation visible
    # here rather than as a side effect of add_column, which matters for downgrade().
    student_type = sa.Enum("rashidi", "quran", name=STUDENT_TYPE_ENUM)
    student_type.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "students",
        sa.Column(
            "student_type",
            sa.Enum("rashidi", "quran", name=STUDENT_TYPE_ENUM, create_type=False),
            nullable=True,
        ),
    )
    op.add_column("students", sa.Column("scoring_preset_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_students_scoring_preset_id", "students", ["scoring_preset_id"], unique=False
    )
    op.create_foreign_key(
        "fk_students_scoring_preset_id_scoring_presets",
        "students",
        "scoring_presets",
        ["scoring_preset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("daily_records", sa.Column("exam_from_line", sa.SmallInteger(), nullable=True))
    op.add_column("daily_records", sa.Column("exam_to_line", sa.SmallInteger(), nullable=True))
    op.create_check_constraint(
        "exam_from_line_positive", "daily_records", "exam_from_line IS NULL OR exam_from_line >= 1"
    )
    op.create_check_constraint(
        "exam_to_line_positive", "daily_records", "exam_to_line IS NULL OR exam_to_line >= 1"
    )


def downgrade() -> None:
    op.drop_constraint("exam_to_line_positive", "daily_records", type_="check")
    op.drop_constraint("exam_from_line_positive", "daily_records", type_="check")
    op.drop_column("daily_records", "exam_to_line")
    op.drop_column("daily_records", "exam_from_line")

    op.drop_constraint(
        "fk_students_scoring_preset_id_scoring_presets", "students", type_="foreignkey"
    )
    op.drop_index("ix_students_scoring_preset_id", table_name="students")
    op.drop_column("students", "scoring_preset_id")
    op.drop_column("students", "student_type")
    sa.Enum(name=STUDENT_TYPE_ENUM).drop(op.get_bind(), checkfirst=True)

    op.drop_table("scoring_presets")
