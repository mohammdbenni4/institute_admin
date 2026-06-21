"""Single import surface for all ORM models.

Alembic autogeneration imports this module so that every table is registered on
``Base.metadata``. Add each new module's models module to the imports below.
"""

from __future__ import annotations

from institute_administration.infrastructure.database.base import Base

# Importing the model modules attaches their tables to ``Base.metadata``.
from institute_administration.modules.daily_records import models as _daily_records  # noqa: F401
from institute_administration.modules.halaqah_types import models as _halaqah_types  # noqa: F401
from institute_administration.modules.halaqahs import models as _halaqahs  # noqa: F401
from institute_administration.modules.identity import models as _identity  # noqa: F401
from institute_administration.modules.scoring import models as _scoring  # noqa: F401
from institute_administration.modules.students import models as _students  # noqa: F401
from institute_administration.modules.teachers import models as _teachers  # noqa: F401
from institute_administration.modules.times import models as _times  # noqa: F401

target_metadata = Base.metadata

__all__ = ["Base", "target_metadata"]
