"""Many-to-many teachers ↔ halaqahs.

Additive. ``halaqahs.teacher_id`` is left exactly as it is — it keeps meaning
«المعلم المسؤول», the single name the paper report prints above its signature
line. What changes is that *access* is no longer read from that column but from
the new ``halaqah_teachers`` table.

The backfill is what makes this safe: every existing halaqah gets one membership
row for its current teacher, so on the first request after deploying, every
teacher sees precisely the halaqahs they saw before — not one more, not one
fewer. No existing row is modified and no column is dropped or retyped.

Revision ID: c7e2a4f81b93
Revises: 8a41c9e0b6d2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "c7e2a4f81b93"
down_revision: str | None = "8a41c9e0b6d2"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "halaqah_teachers",
        sa.Column("halaqah_id", sa.Uuid(), nullable=False),
        sa.Column("teacher_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["halaqah_id"],
            ["halaqahs.id"],
            name="fk_halaqah_teachers_halaqah_id_halaqahs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["teachers.id"],
            name="fk_halaqah_teachers_teacher_id_teachers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("halaqah_id", "teacher_id", name="pk_halaqah_teachers"),
    )
    # Access control asks "which halaqahs does this teacher have?", so the teacher
    # side needs its own index — the composite primary key only serves the halaqah side.
    op.create_index(
        "ix_halaqah_teachers_teacher_id", "halaqah_teachers", ["teacher_id"], unique=False
    )

    # Preserve today's access exactly: each halaqah's current teacher becomes its
    # first member. ON CONFLICT DO NOTHING keeps the migration re-runnable.
    op.execute(
        """
        INSERT INTO halaqah_teachers (halaqah_id, teacher_id, created_at)
        SELECT id, teacher_id, now() FROM halaqahs
        ON CONFLICT (halaqah_id, teacher_id) DO NOTHING
        """
    )


def downgrade() -> None:
    # Only the extra memberships are lost; halaqahs.teacher_id was never touched,
    # so access reverts to exactly what it was before the upgrade.
    op.drop_index("ix_halaqah_teachers_teacher_id", table_name="halaqah_teachers")
    op.drop_table("halaqah_teachers")
