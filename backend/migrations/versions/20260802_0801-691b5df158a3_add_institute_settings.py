"""add institute settings

Adds the single-row ``institute_settings`` table: the institute's own name,
subtitle, contact number, logo and the standing notes printed on the monthly
student report, so the report is not hard-coded to one institute.

Revision ID: 691b5df158a3
Revises: c8d3e4f5a9b2
Create Date: 2026-08-02 08:01:33.723655+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "691b5df158a3"
down_revision: str | None = "c8d3e4f5a9b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# NOTE: autogenerate also proposed dropping `server_default` from a number of
# existing daily_records/scoring_settings columns (pre-existing drift between the
# ORM defaults and the original migrations). That is unrelated to this change and
# is deliberately left out.


def upgrade() -> None:
    op.create_table(
        "institute_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("subtitle", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("report_footer", sa.Text(), nullable=False, server_default=""),
        sa.Column("report_note", sa.Text(), nullable=False, server_default=""),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_institute_settings")),
    )


def downgrade() -> None:
    op.drop_table("institute_settings")
