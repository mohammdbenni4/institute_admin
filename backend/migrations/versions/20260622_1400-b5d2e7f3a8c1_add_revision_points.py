"""Add revision points to scoring_settings and card_revision to daily_records.

Revision ID: b5d2e7f3a8c1
Revises: a3f9b8c2d1e4
Create Date: 2026-06-22 14:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "b5d2e7f3a8c1"
down_revision = "a3f9b8c2d1e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # daily_records: add card_revision snapshot column (default 0 for existing rows)
    op.add_column(
        "daily_records",
        sa.Column("card_revision", sa.SmallInteger(), nullable=False, server_default="0"),
    )

    # scoring_settings: add four revision rating point columns
    op.add_column(
        "scoring_settings",
        sa.Column("revision_4_points", sa.SmallInteger(), nullable=False, server_default="7"),
    )
    op.add_column(
        "scoring_settings",
        sa.Column("revision_3_points", sa.SmallInteger(), nullable=False, server_default="5"),
    )
    op.add_column(
        "scoring_settings",
        sa.Column("revision_2_points", sa.SmallInteger(), nullable=False, server_default="3"),
    )
    op.add_column(
        "scoring_settings",
        sa.Column("revision_1_points", sa.SmallInteger(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("scoring_settings", "revision_1_points")
    op.drop_column("scoring_settings", "revision_2_points")
    op.drop_column("scoring_settings", "revision_3_points")
    op.drop_column("scoring_settings", "revision_4_points")
    op.drop_column("daily_records", "card_revision")
