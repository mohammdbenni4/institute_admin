# تطبيق المعلم — صرح القرآن (frontendMobile)

A mobile-first, RTL Arabic web app for **teachers** to record their students' daily
records (`daily_records`). It talks to the same FastAPI backend as the admin
`frontend`, but is scoped to a single teacher.

## Flow

1. **Login** — teachers only (other roles are rejected after authentication).
2. **My halaqahs** — the circles led by the signed-in teacher.
3. **Students** — the students enrolled in the selected halaqah.
4. **Daily record** — pick a date (defaults to today), create / edit / delete the
   student's daily record, and browse the history of previous days.

## Stack

SvelteKit 2 · Svelte 5 (runes) · TypeScript · Tailwind 3. Material-3 green theme,
IBM Plex Sans Arabic + Material Symbols. Client-rendered SPA (JWT in
`localStorage`, transparent refresh) — see `src/lib/api/`.

## Develop

```bash
npm install
cp .env.example .env      # point PUBLIC_API_BASE_URL at the backend
npm run dev               # http://localhost:5174
```

Quality gates: `npm run check` (svelte-check) · `npm run lint` · `npm run build`.
