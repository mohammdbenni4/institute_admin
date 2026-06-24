---
name: reference-quran-deploy
description: "Quran project production deployment — Hostinger VPS host, layout, and the update runbook"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 089b1a5f-6d6e-4466-a8ed-708feec15d21
---

Production deployment of the Quran project ([[project-quran-overview]]) — **Hostinger VPS, Ubuntu 24.04**.
First deployed 2026-06-23.

**Access**: `ssh root@72.60.131.101` (domain `srv1013493.hstgr.cloud`). **Password is NOT stored here** —
get it from the user each time (root password, shared in chat). No SSH key configured for me; locally there is
no `sshpass`, so connect headlessly via `SSH_ASKPASS` + `setsid -w` (an askpass script that prints the password,
`SSH_ASKPASS_REQUIRE=force`, stdin from /dev/null, `-o StrictHostKeyChecking=accept-new -o PreferredAuthentications=password`).

**Layout** (project at `/root/institute_admin`, a git checkout of `origin/main` = github.com/mohammdbenni4/institute_admin):
- **Backend**: systemd unit `institute_api.service` (uvicorn on `127.0.0.1:8000`), runs from `backend/.venv`
  (pip venv — **there is NO `uv` on the server**; use `backend/.venv/bin/alembic` and `.../uvicorn`). Postgres
  local: db `institute_administration`, user `postgres` (password + JWT in `backend/.env`, `ENVIRONMENT=production`).
- **Admin frontend**: PM2 app `frontend-admin` → `frontend/build/index.js` on `:3000` (adapter-node).
- **Mobile frontend**: PM2 app `frontend-mobile` → `frontendMobile/build/index.js` on `:3001`.
- **Front proxy is Traefik in Docker** (`root-traefik-1`), NOT nginx (nginx is installed but `disabled`/inactive —
  ignore `/etc/nginx/sites-enabled/institute`). Traefik owns :80/:443/:8080; file provider at
  `/root/traefik-dynamic/apps.yml`. Entrypoints: `web`(:80→redirect to https), `websecure`(:443), `mobile`(:8080),
  all TLS via certresolver `mytlschallenge`. Routers (services → `host.docker.internal`): admin `Host(srv…)`→:3000 (443);
  api `Host(srv…)&&PathPrefix(/api/)`→:8000 (443, priority 10); mobile `Host(srv…)`→:3001 on the **`mobile`/:8080** entrypoint.
  So public URLs: admin `https://srv1013493.hstgr.cloud/`, **mobile `https://srv1013493.hstgr.cloud:8080/`** (https, not http), api `…/api/v1/...`.
  `PUBLIC_API_BASE_URL` set per-app in `ecosystem.config.cjs`, read at runtime (`$env/dynamic/public`) — no rebuild to change.
- **Static file trick**: adapter-node serves each app's `build/client/` at site root, so dropping a file there (then
  `pm2 restart frontend-admin`/`-mobile`) exposes it publicly — used to host the APK (see [[project-quran-mobile-offline]]).

**Update runbook** (git-pull model; commit+push to origin from the laptop first):
1. `cd ~/institute_admin && git config pull.rebase false && git fetch origin && git merge origin/main`
   (the server keeps a local `settings` commit — ecosystem/adapter-node/svelte.config — so this is a merge, not ff).
2. **Backup DB first**: `pg_dump -h localhost -U postgres institute_administration > ~/backups/institute_$(date +%F_%H%M%S).sql` (PGPASSWORD from backend/.env).
3. Migrate: `cd backend && .venv/bin/alembic upgrade head`. (New backend deps would need pip install into `.venv`, but none added so far.)
4. `systemctl restart institute_api.service` (verify: routes return 401 when auth-guarded; openapi.json is disabled in prod).
5. Frontends: `cd frontend && npm install && npm run build`; `cd frontendMobile && npm install && npm run build`.
6. `pm2 restart frontend-admin frontend-mobile --update-env && pm2 save`.

**Gotchas**: server `main` is **ahead of origin** (its `settings` commit + merge commits aren't pushed back —
pushing needs GitHub auth on the server). API list `limit` caps at 200. Migrations are irreversible → always pg_dump first.
