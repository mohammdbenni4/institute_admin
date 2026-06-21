# Institute Administration — Backend

FastAPI backend organised with **Domain-Driven Design**. Async **SQLAlchemy 2.0**
(+ asyncpg) over **PostgreSQL**, migrations with **Alembic**, configuration with
**Pydantic Settings**, dependency & environment management with **uv**.

## Architecture

The code follows a layered DDD / hexagonal architecture. The dependency rule
points inward — inner layers never import outer ones.

```
src/institute_administration/
├── core/             # Cross-cutting concerns: configuration, logging
├── shared/           # Shared kernel reused by every bounded context
│   ├── domain/       #   Entity, AggregateRoot, ValueObject, DomainEvent, errors
│   └── application/  #   Command/Query (CQRS), UnitOfWork, errors
├── infrastructure/   # Adapters to the outside world
│   └── database/     #   Engine, session, ORM Base, SqlAlchemyUnitOfWork
├── api/              # Presentation: FastAPI app, routers, error handlers
│   └── v1/           #   Versioned endpoints (health probes today)
├── modules/          # Bounded contexts live here — see modules/README.md
└── main.py           # ASGI app + dev-server entry point
```

Layer responsibilities:

| Layer            | May depend on            | Knows about                                  |
| ---------------- | ------------------------ | -------------------------------------------- |
| `domain`         | (nothing)                | Business rules, invariants, events           |
| `application`    | `domain`                 | Use cases, ports, transactions               |
| `infrastructure` | `application`, `domain`  | SQLAlchemy, asyncpg, external services        |
| `api`            | all of the above         | HTTP, serialization, dependency injection    |

Features live as bounded contexts under
[`src/institute_administration/modules/`](src/institute_administration/modules/README.md).

## Domain model

All primary keys are **UUID** (never integers). The app is **Arabic-only**:
domain error messages are Arabic and text is sorted with an `arabic` ICU
collation.

| Table           | Summary                                                                       |
| --------------- | ----------------------------------------------------------------------------- |
| `users`         | `full_name`, `email`, `password_hash`, `role` (`super_admin`/`teacher`), `date_of_birth?`, `is_active` |
| `teachers`      | 1:1 `user_id`, `academic_study`, `islamic_study`, `is_assistant`              |
| `students`      | `full_name`, `father_name/number`, `mother_number?`, `orphan_of?` (father/mother/both), `residential_area?`, `accepted_at?`, `notes?`, `halaqah_id?` — **no login** |
| `halaqahs`      | `name`, `teacher_id`, `halaqah_type_id`, `level?`, `age?`, `time_id?`; student count is **computed** |
| `halaqah_types` | `name` (unique)                                                               |
| `times`         | `name` + one JSONB column per weekday (Sat→Fri), each `{ "from": "HH:MM", "to": "HH:MM" }` |

## Authentication

JWT (access + refresh) with argon2 password hashing. `POST /api/v1/auth/login`
returns the token pair; send `Authorization: Bearer <access_token>`. Reads
require any authenticated user; writes require `super_admin`.

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- PostgreSQL 16 (locally installed, or via `docker compose up -d`)

## Getting started

```bash
# 1. Install dependencies (creates .venv automatically)
make install            # == uv sync

# 2. Configure environment
cp .env.example .env     # then edit credentials as needed

# 3. Provision the database
#    a) locally installed Postgres (using the postgres superuser / password "postgres"):
sudo -u postgres psql -c "ALTER ROLE postgres WITH PASSWORD 'postgres';"
sudo -u postgres createdb institute_administration --owner postgres
#    b) or with Docker:
docker compose up -d

# 4. Apply migrations (creates all tables + the Arabic collation)
make migrate

# 5. Seed the bootstrap super-admin (SuperAdmin@gmail.com / admin)
make seed

# 6. Run the API (http://localhost:8000, docs at /docs)
make dev
```

## Common tasks

| Command                              | Description                              |
| ------------------------------------ | ---------------------------------------- |
| `make dev`                           | Run the API with autoreload              |
| `make test`                          | Run the test suite                       |
| `make check`                         | Lint + type-check + test (all gates)     |
| `make format`                        | Format code and fix imports              |
| `make migration m="add x"`           | Autogenerate a migration                 |
| `make migrate` / `make downgrade`    | Apply / revert migrations                |
| `make seed`                          | Create the bootstrap super-admin         |

Health probes once running:

- Liveness:  `GET /api/v1/health`
- Readiness: `GET /api/v1/health/ready` (verifies the database connection)

## Testing

```bash
make test          # unit + integration
make test-cov      # with coverage report
```

Integration tests for the HTTP layer use an in-process ASGI transport and need
no running server. Tests that exercise the database expect a reachable Postgres
configured via `.env`.
