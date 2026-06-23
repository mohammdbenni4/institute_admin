"""add problems and daily_record_problems tables

Revision ID: c8d3e4f5a9b2
Revises: b5d2e7f3a8c1
Create Date: 2026-06-22 16:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "c8d3e4f5a9b2"
down_revision = "b5d2e7f3a8c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "problem_levels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
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
    )

    op.create_table(
        "problems",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("problem_level_id", UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["problem_level_id"],
            ["problem_levels.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("name", "problem_level_id", name="uq_problems_name_level"),
    )
    op.create_index("ix_problems_problem_level_id", "problems", ["problem_level_id"])

    op.create_table(
        "daily_record_problems",
        sa.Column("daily_record_id", UUID(as_uuid=True), nullable=False),
        sa.Column("problem_id", UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["daily_record_id"],
            ["daily_records.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["problem_id"],
            ["problems.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("daily_record_id", "problem_id"),
    )


def downgrade() -> None:
    op.drop_table("daily_record_problems")
    op.drop_index("ix_problems_problem_level_id", table_name="problems")
    op.drop_table("problems")
    op.drop_table("problem_levels")
