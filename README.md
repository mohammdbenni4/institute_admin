# Institute Administration

Full-stack Institute Administration application:

| Folder                   | Stack                                              |
| ------------------------ | -------------------------------------------------- |
| [`backend/`](backend/)   | FastAPI · DDD · async SQLAlchemy · PostgreSQL · uv |
| [`frontend/`](frontend/) | SvelteKit (Svelte 5) · TypeScript · Vite           |

Both folders are independent and start **blank** — only the architecture,
tooling and wiring are in place. See each folder's `README.md` to get started:

- Backend → [`backend/README.md`](backend/README.md)
- Frontend → [`frontend/README.md`](frontend/README.md)

## Quick start

```bash
# Backend (http://localhost:8000)
cd backend && make install && cp .env.example .env && make dev

# Frontend (http://localhost:5173)
cd frontend && npm install && cp .env.example .env && npm run dev
```
