# Project Memory

Durable, git-tracked notes for صرح القرآن. Session logs + decisions live here so
anyone (and any future AI session) can read the project's history quickly.

> Note: local-only dev credentials are kept out of this repo folder on purpose.
> They live in the machine-local memory (`~/.claude/projects/.../memory/`), not here.

## Sessions
- [2026-06-22](sessions/2026-06-22.md) — daily_records, teacher mobile app, admin analytics/profiles, teacher scoping, bulk attendance, configurable scoring, halaqah filters, WhatsApp link.

## Architecture (quick reference)
- **backend/** — FastAPI + SQLAlchemy(async) + Alembic + Postgres. DDD-lite modules under
  `src/institute_administration/modules/` (identity, teachers, students, halaqahs,
  halaqah_types, times, daily_records, analytics, scoring). Run gates with `export PYTHONPATH= && uv run ...`.
- **frontend/** — admin dashboard (SvelteKit 2 + Svelte 5 + Tailwind, shadcn-style, RTL). Port 5173.
- **frontendMobile/** — teacher-only app (Material-3 green Stitch theme). Port 5174.

## Core domain rules
- One `daily_record` per (student, date). Reward-card total = present + exam + attitude + added_points.
- Card scores are a **snapshot** of the scoring policy at write time (changing weights never rewrites history).
- Scoring weights are configurable (`scoring_settings` table, admin-editable).
- Teacher scoping: teachers only see/edit their own halaqahs' data (super admins unrestricted).

## Code knowledge graph (graphify)
A queryable map of the codebase lives in `graphify-out/` (built with `graphify`, no API cost):
- `graph.json` — 1641 nodes / 3239 edges / 123 communities (functions, classes, modules + relations).
- `GRAPH_REPORT.md` — human-readable community/navigation report.
- `graph.html` — interactive visualization (open in a browser).

Use it (run from the project root):
- `graphify query "<question>"` — BFS traversal returning the relevant code nodes/edges.
- `graphify explain "<Symbol>"` — plain-language explanation of a node + neighbors.
- `graphify path "A" "B"` — shortest path between two symbols.
- `graphify affected "<Symbol>"` — what depends on a symbol (reverse traversal).
- `graphify update .` — rebuild after code changes (deterministic, no LLM).

## Open threads
See the latest session log's "Open Threads" section.
