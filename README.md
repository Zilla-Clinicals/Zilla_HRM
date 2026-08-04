# Zilla Clinicals — HRM

Lightweight Human Resource Management app for Zilla Clinicals. Two things matter:
**inviting company users** and **running performance reviews twice a year**.

Stack: React 19 + Vite + TypeScript (frontend) · FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 (backend).
Own auth (Argon2id + JWT access + rotating refresh cookie). No Docker in the app, no third-party IDP.

See [HRM_TECHNICAL_DESIGN.md](HRM_TECHNICAL_DESIGN.md) for the full design.

## Quickstart

### Prerequisites
- Python 3.12+, `uv`
- Node 20+, npm 10+
- PostgreSQL 16 (native, or one Docker container just for the DB)

Spin up a local Postgres (DB only) with Docker:

```bash
docker run -d --name zillahrm-db -p 5432:5432 \
  -e POSTGRES_USER=hrm -e POSTGRES_PASSWORD=hrm -e POSTGRES_DB=hrm \
  postgres:16-alpine
```

### Backend

```bash
cd backend
cp .env.example .env          # fill DATABASE_URL, JWT_SECRET, RESEND_API_KEY
uv sync
uv run alembic upgrade head
uv run python -m scripts.create_hr_admin --email admin@zillaclinicals.com --password "ChangeMe123!" --name "HR Admin"
uv run uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
cp .env.example .env          # VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev
# → http://localhost:5173
```

## Roles
- **hr_admin** — everything: invites, KPIs, cycles, all results
- **manager** — reviews their direct reports each cycle
- **employee** — logs in, sees own profile + review history

## CI
- `.github/workflows/backend.yml` — ruff + pytest against a Postgres service on every backend change
- `.github/workflows/frontend.yml` — typecheck + build on every frontend change

## Deploy (no Docker)
- **Backend + DB** → Render via [`render.yaml`](render.yaml). It provisions managed Postgres, runs
  `alembic upgrade head` as a pre-deploy step, and health-checks `/health`. Set `RESEND_API_KEY`
  in the dashboard. `DATABASE_URL` is injected as `postgresql://…` and auto-upgraded to the asyncpg
  driver in `app/config.py`.
- **Frontend** → Vercel with root directory `frontend/` (see [`frontend/vercel.json`](frontend/vercel.json)).
  Set `VITE_API_BASE_URL` to the Render URL.
- Because the two live on different domains, prod sets the refresh cookie `SameSite=None; Secure`
  (already wired in `render.yaml`). Update `CORS_ORIGINS` / `APP_BASE_URL` to your real Vercel domain.

After the first deploy, create the initial admin from the Render shell:
`uv run python -m scripts.create_hr_admin --email you@company.com --password '…' --name 'You'`.
