"""add excused absence: daily_records.excused + scoring_settings absence points

Revision ID: a3f9b8c2d1e4
Revises: 886108024f77
Create Date: 2026-06-22 12:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3f9b8c2d1e4"
down_revision: str | None = "886108024f77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A third attendance state: excused absence (أذن).
    op.add_column(
        "daily_records",
        sa.Column("excused", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Enforce: a student cannot be present AND excused at the same time.
    op.create_check_constraint(
        "excused_requires_absent",
        "daily_records",
        "NOT (present AND excused)",
    )

    # Configurable points for unexcused and excused absences.
    op.add_column(
        "scoring_settings",
        sa.Column("absent_points", sa.SmallInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "scoring_settings",
        sa.Column("excused_points", sa.SmallInteger(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("scoring_settings", "excused_points")
    op.drop_column("scoring_settings", "absent_points")
    op.drop_constraint("excused_requires_absent", "daily_records", type_="check")
    op.drop_column("daily_records", "excused")
