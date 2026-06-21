# Bounded contexts (`modules/`)

Each module is an independent **bounded context**. The dependency rule points
**inward**: presentation → application → domain; infrastructure implements the
domain's ports. Layers are separated **by file** (rather than deep folders) to
keep each context easy to navigate:

```
modules/<context>/
├── __init__.py
├── domain.py        # Domain: entity/aggregate, value objects, repository PORT (ABC), errors
├── service.py       # Application: use-case service(s) + input DTOs (+ read models)
├── models.py        # Infrastructure: SQLAlchemy ORM model(s)
├── repository.py    # Infrastructure: repository implementation + entity<->model mapping
├── schemas.py       # Presentation: Pydantic request/response models
└── router.py        # Presentation: FastAPI endpoints + dependency wiring
```

The `identity` context additionally has `dependencies.py` (auth guards:
`get_current_user`, `require_roles`, `CurrentSuperAdmin`) which other contexts
import to protect their endpoints.

## The contexts

| Module           | Aggregate(s)   | Notes                                            |
| ---------------- | -------------- | ------------------------------------------------ |
| `identity`       | `User`         | Roles (`super_admin`, `teacher`) + JWT auth      |
| `teachers`       | `Teacher`      | 1:1 with a `User`; create makes both atomically  |
| `students`       | `Student`      | No login; references a halaqah by id (nullable)  |
| `halaqahs`       | `Halaqah`      | Joins teacher/type names; live student count     |
| `halaqah_types`  | `HalaqahType`  | Simple reference data                            |
| `times`          | `Time`         | Weekly schedule, one JSONB column per day        |

## Conventions

- **UUID primary keys everywhere** (`UUIDPrimaryKeyMixin`) — never integers.
- **Timestamps** via `TimestampMixin` (`created_at` / `updated_at`).
- **Cross-context references are by id only.** A repository may join another
  context's table for a read model (e.g. `halaqahs` joins `teachers`/`users`),
  but aggregates never import each other.
- **Arabic** error messages in the domain; Arabic-aware ordering via the
  `arabic` ICU collation in list queries.
- Writes require `super_admin`; reads require any authenticated user.

## Adding a context

1. Create the six files above following an existing module (e.g. `halaqah_types`).
2. Register the ORM models in
   [`infrastructure/database/metadata.py`](../infrastructure/database/metadata.py).
3. `make migration m="add <context>"` then `make migrate`.
4. Mount the router in [`api/v1/router.py`](../api/v1/router.py).

Shared building blocks live in [`institute_administration.shared`](../shared)
(`AggregateRoot`, `ValueObject`, `Command`/`Query`, `Page`, `UNSET`, errors).
