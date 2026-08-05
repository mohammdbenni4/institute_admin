"""exam_total supports half pages

Teachers count recitation in halves and quarters («نصف صفحة»), but the column was a
SMALLINT, so `0.5` was rejected and the teacher saw a raw validation error. Widening
it to NUMERIC(6,2) is the actual fix.

NOTE: unlike the other migrations in this batch this one **rewrites the table** and
holds an ACCESS EXCLUSIVE lock for the duration — it is a type change, not an added
column. Cheap at this data size, but run it when nobody is recording.

Autogenerate also proposed dropping `server_default` from unrelated columns; that is
pre-existing drift and is deliberately left out.

Revision ID: 54d2f535295b
Revises: 1b37cd5065f0
Create Date: 2026-08-05 12:07:42.254602+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "54d2f535295b"
down_revision: str | None = "1b37cd5065f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `USING` is required: Postgres will not silently reinterpret smallint as numeric.
    op.alter_column(
        "daily_records",
        "exam_total",
        existing_type=sa.SMALLINT(),
        type_=sa.Numeric(6, 2),
        existing_nullable=True,
        postgresql_using="exam_total::numeric(6,2)",
    )


def downgrade() -> None:
    # Half pages cannot survive the narrower type; round to the nearest whole page.
    op.alter_column(
        "daily_records",
        "exam_total",
        existing_type=sa.Numeric(6, 2),
        type_=sa.SMALLINT(),
        existing_nullable=True,
        postgresql_using="round(exam_total)::smallint",
    )
