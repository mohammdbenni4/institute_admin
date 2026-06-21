# Institute Administration — Frontend

**SvelteKit** (Svelte 5 runes) + **TypeScript** + **Tailwind CSS** — a
right‑to‑left (Arabic) **admin dashboard** for the institute. Only the
**super admin** signs in; every screen is full CRUD wired to the FastAPI backend
in [`../backend`](../backend). Runs as a client-rendered SPA (`ssr = false`).

## Prerequisites

- Node.js 20+ and npm
- The backend running (see [`../backend/README.md`](../backend/README.md)) with a
  seeded super-admin account.

## Getting started

```bash
npm install               # install dependencies
cp .env.example .env       # set PUBLIC_API_BASE_URL (default points at the backend)
npm run dev                # http://localhost:5173
```

Sign in at `/login` with the super-admin credentials; non-super-admin accounts
are rejected. The index `/` redirects to `/admin`, which guards every page and
sends unauthenticated visitors to `/login`.

## Scripts

| Command           | Description                      |
| ----------------- | -------------------------------- |
| `npm run dev`     | Start the dev server (port 5173) |
| `npm run build`   | Production build                 |
| `npm run preview` | Preview the production build     |
| `npm run check`   | Type-check with `svelte-check`   |
| `npm run lint`    | Prettier + ESLint                |
| `npm run format`  | Format with Prettier             |

## Routes

| Route                  | Purpose                                |
| ---------------------- | -------------------------------------- |
| `/login`               | Super-admin sign in (JWT)              |
| `/admin`               | Dashboard — record counts per resource |
| `/admin/users`         | Users CRUD                             |
| `/admin/teachers`      | Teachers CRUD                          |
| `/admin/students`      | Students CRUD                          |
| `/admin/halaqahs`      | Halaqahs CRUD                          |
| `/admin/halaqah-types` | Halaqah types CRUD                     |
| `/admin/times`         | Times CRUD (per-weekday windows)       |

Each list page maps 1:1 to a backend module and supports create, edit and
delete; writes require the super-admin role on the server.

## Structure

```
src/
├── app.html                  # HTML shell (lang="ar" dir="rtl", Cairo font)
├── app.css                   # Tailwind layers + design tokens (HSL theme)
├── lib/
│   ├── api/                  # Backend client
│   │   ├── client.ts         #   fetch wrapper: JWT storage + refresh + errors
│   │   ├── types.ts          #   TypeScript mirrors of the API schemas
│   │   ├── resources.ts      #   typed CRUD per resource
│   │   ├── auth.svelte.ts    #   reactive auth store (login/logout/loadCurrentUser)
│   │   └── index.ts
│   ├── labels.ts             # Arabic enum labels + date formatting
│   ├── utils.ts              # `cn()` class-merge helper
│   ├── actions/              # Svelte actions (clickOutside)
│   └── components/
│       ├── ui/               # Primitives: Button, Input, Label, Select, Switch, Dialog, Popover
│       └── shared/           # PageHeader, FilterBar, DataTable, StatusBadge, KPICard, ConfirmDialog, RoleLayout, TopHeader
└── routes/                   # File-based routing (login + /admin/* CRUD)
```

## Tech notes

- **Auth** — JWT access/refresh tokens in `localStorage`; the client injects the
  bearer header and transparently refreshes once on a 401.
- **Styling** — Tailwind CSS 3 with shadcn-style HSL CSS variables; RTL by default.
- **Icons** — [`@lucide/svelte`](https://lucide.dev).
- The interactive primitives (dialog, select, popover, switch) are hand-built —
  no runtime UI dependency beyond Tailwind/lucide.
