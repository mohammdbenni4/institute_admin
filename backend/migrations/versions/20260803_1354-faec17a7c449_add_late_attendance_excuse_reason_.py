"""add late attendance, excuse reason, signed points

Three related changes:

* ``daily_records.late`` — «متأخر» as a qualifier on attendance. A late student is
  still present, so the column is a flag rather than a fourth state; existing rows
  backfill to ``false`` and keep their meaning.
* ``daily_records.excuse_reason`` — why an absence was excused (أذن). Nullable
  because records written before this column existed have no reason to record.
* ``added_points`` becomes signed — teachers deduct as well as award — so the
  ``>= 0`` CHECK is dropped, and ``scoring_settings.late_points`` is added so the
  institute can price lateness itself.

Revision ID: faec17a7c449
Revises: 691b5df158a3
Create Date: 2026-08-03 13:54:36.822064+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "faec17a7c449"
down_revision: str | None = "691b5df158a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# NOTE: autogenerate additionally proposed dropping `server_default` from a number
# of pre-existing daily_records/scoring_settings/institute_settings columns. That is
# unrelated drift between the ORM defaults and the original migrations and is
# deliberately left out. It also cannot see CHECK constraints, so those are written
# by hand below.


def upgrade() -> None:
    # `server_default` is required: these tables already hold rows, and a NOT NULL
    # column without one cannot be added.
    op.add_column(
        "daily_records",
        sa.Column("late", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("daily_records", sa.Column("excuse_reason", sa.Text(), nullable=True))
    op.create_check_constraint(
        "late_requires_present", "daily_records", "NOT (late AND NOT present)"
    )

    # Points are now signed («إضافة النقاط وحذفها بشكل كامل»).
    op.drop_constraint("added_points_non_negative", "daily_records", type_="check")

    op.add_column(
        "scoring_settings",
        sa.Column("late_points", sa.SmallInteger(), nullable=False, server_default="5"),
    )


def downgrade() -> None:
    op.drop_column("scoring_settings", "late_points")
    # Deducted points cannot survive the old constraint; clamp before restoring it.
    op.execute("UPDATE daily_records SET added_points = 0 WHERE added_points < 0")
    op.create_check_constraint(
        "added_points_non_negative", "daily_records", "added_points >= 0"
    )
    op.drop_constraint("late_requires_present", "daily_records", type_="check")
    op.drop_column("daily_records", "excuse_reason")
    op.drop_column("daily_records", "late")
