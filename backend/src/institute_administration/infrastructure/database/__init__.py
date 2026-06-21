"""Database infrastructure: SQLAlchemy engine, session, ORM base and unit of work.

When you add ORM models for a bounded context, import them in
:mod:`institute_administration.infrastructure.database.metadata` so that they are registered on the
shared ``Base.metadata`` and picked up by Alembic autogeneration.
"""

from institute_administration.infrastructure.database.base import Base
from institute_administration.infrastructure.database.session import (
    get_engine,
    get_session_factory,
)
from institute_administration.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork

__all__ = [
    "Base",
    "SqlAlchemyUnitOfWork",
    "get_engine",
    "get_session_factory",
]
