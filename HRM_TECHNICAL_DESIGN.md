# HRM System — Fresh Build Technical Design

> Self-contained blueprint for building a lightweight HRM (Human Resource Management) app from scratch. Focused on the two features that actually matter: **inviting company users** and **running performance reviews twice a year**.
>
> **No Docker. No Supabase. No third-party identity provider.** React + FastAPI + PostgreSQL, own auth, per-language dependency isolation (uv + npm).
>
> Meant to be dropped into a fresh working folder and used as the sole guide. Every design choice is one-line-justified. Every deferrable feature is explicitly called out.

---

## 1. What we're building

An internal web app for a company's HR team to (a) manage employee accounts and (b) run structured performance reviews on a fixed twice-yearly cadence.

### 1.1 Primary users

| Role | Cares about |
|---|---|
| **HR admin** | Creating review cycles, inviting employees, defining KPIs, viewing all results |
| **Manager / team lead** | Evaluating their direct reports each cycle |
| **Employee** | Logging in, seeing profile + own past reviews, completing self-assessment |

### 1.2 The twice-a-year cadence

Two review cycles per calendar year:
- `mid_year` — typically opened in June, closes end of July
- `end_year` — typically opened in December, closes end of January

An HR admin opens a cycle, assigns each employee's reviewer, and everyone completes their part within the window. Once the cycle closes, all data is read-only. Historical cycles are visible per employee.

That's it. Everything else is optional.

---

## 2. MVP feature list

### 2.1 In scope for v1

1. **Auth** — email + password login, admin-only invites, password reset via email
2. **User & employee management** — invite, deactivate, list, edit contact info
3. **KPI catalog** — HR maintains a list of things being rated (e.g. "Task completion rate", "Communication", "Technical skills")
4. **Review cycle lifecycle** — create cycle, assign reviewers to employees, open cycle, close cycle
5. **Review flow** — reviewer opens their assigned employees, scores each KPI + writes a comment, submits
6. **History view** — per-employee: list of past cycles with total score, drill in for KPI breakdown
7. **Basic dashboard** — HR view: cycle status, completion rate, distribution histogram

### 2.2 Explicitly out of scope for v1

If the team asks for these later, we add them. Do not build them now.

- Learning / training tracking (courses, enrollments)
- 360-degree feedback (peer reviews)
- Employee-authored surveys
- Career path planning
- Personal goals with progress tracking
- Advanced analytics (start with basic tables + one bar chart)
- MFA / SSO
- Email notifications beyond password reset & invitation
- File uploads (avatars, attachments)
- Audit log / activity feed

Cutting these keeps v1 at ~2–3 focused weeks for one developer.

---

## 3. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend framework | **React 19 + Vite + TypeScript** | Fast dev server, modern React, strong typing |
| Styling | **Tailwind CSS 3.4** | Utility-first, no design-system overhead |
| Charts (dashboard) | **Recharts** | One dependency, sufficient for basic bar/line charts |
| Frontend router | **react-router 7** | The obvious choice for an SPA |
| Backend framework | **FastAPI (Python 3.12+)** | Async, Pydantic-typed I/O, auto OpenAPI |
| ORM | **SQLAlchemy 2.0 (async, declarative)** | Type-safe query builder, works with Alembic |
| DB driver | **asyncpg** | Fastest async Postgres driver |
| Migrations | **Alembic** | Standard for SQLAlchemy; app-owned schema versioning |
| Database | **PostgreSQL 16** | The default answer |
| Auth | **Own**: Argon2id password hashing + short-lived JWT + rotating refresh token in httpOnly cookie | No IDP dependency; standard, secure, testable |
| Email delivery | **Resend** (or Postmark / Mailgun) | SMTP for password reset + invite; simplest transactional provider |
| Backend deps isolation | **uv** — creates project-local `.venv/` | Fast, deterministic, no Docker |
| Frontend deps isolation | **npm** — project-local `node_modules/` | Standard; deterministic via `package-lock.json` |
| Local Postgres | Native install **or** one Docker container for the DB only | Not the app — just the DB. Or use Neon dev branch. |
| Deployment (frontend) | **Vercel** (or Cloudflare Pages / Netlify) | Free tier, git-triggered deploys, CDN |
| Deployment (backend) | **Render** or **Fly.io** or **Railway** | Deploys Python from source with `uv sync`; free tiers exist |
| Deployment (DB) | **Neon** (managed Postgres, free tier) **or** the platform's built-in Postgres | Managed → no ops burden |
| CI/CD | **GitHub Actions** | Free, standard |

**No Docker in the app image**. Backend runs from `uv sync` on the platform's build step; frontend is a static Vite build. If you want a local Postgres and don't want to install it natively, one Docker container just for `postgres:16-alpine` is a fine escape hatch — the app itself remains Docker-free.

---

## 4. Repository layout

```
hrm/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app; mounts routers
│   │   ├── config.py               # pydantic-settings; reads .env
│   │   ├── db.py                   # async engine, session factory, Base
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── passwords.py        # Argon2id hash + verify
│   │   │   ├── tokens.py           # JWT sign + verify (RS256 or HS256)
│   │   │   ├── deps.py             # get_current_user, require_role
│   │   │   └── email.py            # Resend/SMTP send_invite, send_reset
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── _base.py            # mixins, enums
│   │   │   ├── users.py            # User, Invitation, PasswordReset, RefreshToken
│   │   │   ├── employees.py        # Employee
│   │   │   ├── kpis.py             # Kpi
│   │   │   └── reviews.py          # ReviewCycle, ReviewAssignment, ReviewScore
│   │   ├── schemas/                # Pydantic request/response models
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── employees.py
│   │   │   ├── kpis.py
│   │   │   └── reviews.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # /login, /refresh, /logout, /reset-password
│   │   │   ├── users.py            # /me, /users, /users/invite
│   │   │   ├── employees.py        # /employees CRUD
│   │   │   ├── kpis.py             # /kpis CRUD
│   │   │   ├── reviews.py          # /cycles, /reviews
│   │   │   └── dashboard.py        # /dashboard/cycle/{id}
│   │   └── services/
│   │       ├── invitations.py      # create_invitation, consume_invitation
│   │       └── reviews.py          # cycle open/close, score aggregation
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── tests/
│   │   ├── conftest.py             # PG testcontainer + JWT helper
│   │   ├── test_auth.py
│   │   ├── test_users.py
│   │   ├── test_employees.py
│   │   ├── test_kpis.py
│   │   └── test_reviews.py
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .env.example
│   └── .env                        # gitignored
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                 # routes + AuthProvider
│   │   ├── lib/
│   │   │   ├── apiClient.ts        # typed fetch wrapper (auto JWT)
│   │   │   └── auth.ts             # login, logout, refresh helpers
│   │   ├── auth/
│   │   │   ├── AuthProvider.tsx    # session context
│   │   │   ├── ProtectedRoute.tsx
│   │   │   └── useAuth.ts
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── AcceptInvite.tsx    # set password from invite link
│   │   │   ├── ForgotPassword.tsx
│   │   │   ├── ResetPassword.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Employees.tsx       # list + create/edit modal
│   │   │   ├── EmployeeProfile.tsx # single employee + past reviews
│   │   │   ├── Kpis.tsx            # HR-only
│   │   │   ├── ReviewCycles.tsx    # HR-only: list, create, open, close
│   │   │   ├── DoReview.tsx        # reviewer-facing form
│   │   │   └── SecuritySettings.tsx # change password
│   │   ├── components/
│   │   │   ├── Layout.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   └── charts/
│   │   │       └── ScoreDistribution.tsx
│   │   └── shared/
│   │       ├── api-types.ts        # generated from FastAPI OpenAPI (optional but recommended)
│   │       └── types.ts            # hand-written form/UI types
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   ├── package.json
│   ├── package-lock.json
│   ├── .env.example
│   └── .env                        # gitignored
│
├── .github/
│   └── workflows/
│       ├── backend.yml             # lint + test + deploy
│       └── frontend.yml            # lint + build + deploy
├── .gitignore
└── README.md
```

**No `docker-compose.yml`. No `Dockerfile`.** Both services run natively via `uv` and `npm`.

---

## 5. Data model

Seven core tables. Postgres native types throughout — booleans, TIMESTAMPTZ, native enums, JSONB where useful.

### 5.1 Enums

```
role_enum:          'hr_admin' | 'manager' | 'employee'
cycle_type_enum:    'mid_year' | 'end_year'
cycle_status_enum:  'draft' | 'open' | 'closed'
review_status_enum: 'not_started' | 'in_progress' | 'submitted'
```

Three roles is the MVP simplification (down from four in the original codebase). `hr_admin` does everything; `manager` reviews their reports; `employee` logs in, sees their history.

### 5.2 Tables

**`users`** — identity + auth

| column | type | notes |
|---|---|---|
| id | BIGSERIAL PK | |
| email | TEXT NOT NULL UNIQUE | citext-lowercased on insert |
| password_hash | TEXT | NULL until user accepts invite |
| role | role_enum NOT NULL DEFAULT 'employee' | |
| is_active | BOOLEAN NOT NULL DEFAULT true | soft-deactivate on offboard |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ NOT NULL DEFAULT now() | trigger-maintained |

**`invitations`** — pending invites (one-time-use tokens)

| column | type | notes |
|---|---|---|
| id | BIGSERIAL PK | |
| email | TEXT NOT NULL | |
| role | role_enum NOT NULL | |
| token_hash | TEXT NOT NULL UNIQUE | sha256 of the raw token; raw goes in the email link only |
| invited_by | BIGINT REFERENCES users(id) ON DELETE SET NULL | |
| expires_at | TIMESTAMPTZ NOT NULL | typically now() + 7 days |
| accepted_at | TIMESTAMPTZ NULL | NULL until consumed |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**`password_resets`** — same pattern as invitations, one-time-use

| column | type | notes |
|---|---|---|
| id | BIGSERIAL PK | |
| user_id | BIGINT REFERENCES users(id) ON DELETE CASCADE | |
| token_hash | TEXT NOT NULL UNIQUE | |
| expires_at | TIMESTAMPTZ NOT NULL | now() + 1 hour |
| consumed_at | TIMESTAMPTZ NULL | |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**`refresh_tokens`** — server-side refresh token registry (enables revoke on logout)

| column | type | notes |
|---|---|---|
| id | BIGSERIAL PK | |
| user_id | BIGINT REFERENCES users(id) ON DELETE CASCADE | |
| token_hash | TEXT NOT NULL UNIQUE | sha256 of the raw token |
| user_agent | TEXT | for a future "active sessions" screen |
| expires_at | TIMESTAMPTZ NOT NULL | now() + 30 days |
| revoked_at | TIMESTAMPTZ NULL | populated on logout / rotation |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**`employees`** — HR-owned record (1:1 with users)

| column | type | notes |
|---|---|---|
| id | BIGSERIAL PK | |
| user_id | BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE | |
| full_name | TEXT NOT NULL | |
| job_title | TEXT | |
| team | TEXT | |
| hire_date | DATE | |
| phone | TEXT | |
| manager_id | BIGINT REFERENCES employees(id) ON DELETE SET NULL | self-reference; who reviews them |
| created_at, updated_at | TIMESTAMPTZ | |

**`kpis`** — HR maintains this catalog

| column | type | notes |
|---|---|---|
| id | BIGSERIAL PK | |
| name | TEXT NOT NULL | |
| category | TEXT NOT NULL | e.g. "Productivity", "Behavior" |
| description | TEXT | |
| weight | NUMERIC(5,2) NOT NULL DEFAULT 1.00 | contribution to weighted total |
| is_active | BOOLEAN NOT NULL DEFAULT true | soft-hide |
| created_at, updated_at | TIMESTAMPTZ | |

**`review_cycles`** — one row per (year, type) pair

| column | type | notes |
|---|---|---|
| id | BIGSERIAL PK | |
| year | INTEGER NOT NULL | |
| type | cycle_type_enum NOT NULL | |
| status | cycle_status_enum NOT NULL DEFAULT 'draft' | |
| opens_at | TIMESTAMPTZ NOT NULL | when reviewers can start |
| closes_at | TIMESTAMPTZ NOT NULL | after this, no edits |
| created_by | BIGINT REFERENCES users(id) ON DELETE SET NULL | |
| created_at, updated_at | TIMESTAMPTZ | |

Composite unique on `(year, type)`.

**`review_assignments`** — reviewer ↔ subject for a cycle

| column | type | notes |
|---|---|---|
| id | BIGSERIAL PK | |
| cycle_id | BIGINT NOT NULL REFERENCES review_cycles(id) ON DELETE CASCADE | |
| subject_employee_id | BIGINT NOT NULL REFERENCES employees(id) ON DELETE CASCADE | |
| reviewer_employee_id | BIGINT NOT NULL REFERENCES employees(id) ON DELETE CASCADE | usually = subject.manager_id |
| status | review_status_enum NOT NULL DEFAULT 'not_started' | |
| submitted_at | TIMESTAMPTZ NULL | |
| summary_comment | TEXT | reviewer's overall note |
| created_at, updated_at | TIMESTAMPTZ | |

Composite unique on `(cycle_id, subject_employee_id)`.

**`review_scores`** — one row per (assignment, kpi)

| column | type | notes |
|---|---|---|
| id | BIGSERIAL PK | |
| assignment_id | BIGINT NOT NULL REFERENCES review_assignments(id) ON DELETE CASCADE | |
| kpi_id | BIGINT NOT NULL REFERENCES kpis(id) ON DELETE RESTRICT | |
| score | NUMERIC(4,2) NOT NULL | 0.00–5.00 scale |
| comment | TEXT | |
| created_at, updated_at | TIMESTAMPTZ | |

Composite unique on `(assignment_id, kpi_id)`.

### 5.3 Common patterns

- Every table has `created_at` + `updated_at` (TIMESTAMPTZ, server-default `now()`)
- A single `set_updated_at()` trigger function installed by migration 0001; per-table triggers wired to it
- Foreign keys always specify `ON DELETE` explicitly (CASCADE / SET NULL / RESTRICT)
- Indexes on every FK column, plus `employees(manager_id)`, `review_assignments(cycle_id, status)`, `review_scores(assignment_id)`

---

## 6. API surface

Every route is documented in FastAPI's auto-generated OpenAPI. This is the exhaustive list.

**Auth (public — no JWT required)**
- `POST /api/auth/login` — email + password → `{access_token, refresh set as httpOnly cookie}`
- `POST /api/auth/refresh` — reads refresh cookie → new access + new refresh (rotate)
- `POST /api/auth/logout` — revokes refresh; clears cookie
- `POST /api/auth/forgot-password` — email → 202 (always; don't leak which emails exist)
- `POST /api/auth/reset-password` — `{token, new_password}` → 204
- `POST /api/auth/accept-invite` — `{token, full_name, password}` → 204 + logs the user in

**Users (JWT required)**
- `GET /api/users/me` — current user + linked employee
- `PATCH /api/users/me` — self-update (name, phone)
- `POST /api/users/me/password` — change own password (requires current)
- `GET /api/users` — admin only; list all users
- `POST /api/users/invite` — admin only; `{email, role, initial_employee: {...}}` → creates invitation + sends email
- `PATCH /api/users/{id}` — admin only; toggle is_active, change role
- `DELETE /api/users/{id}` — admin only; deactivates (never hard-deletes)

**Employees (JWT required)**
- `GET /api/employees` — list, filter by team / active
- `GET /api/employees/{id}` — employees see own; managers see reports; HR sees all
- `PATCH /api/employees/{id}` — HR only for now (later: manager can edit reports)
- `GET /api/employees/{id}/reviews` — history: all assignments + summaries

**KPIs (JWT required)**
- `GET /api/kpis` — list active
- `POST /api/kpis` — HR only; create
- `PATCH /api/kpis/{id}` — HR only; edit weight/description/is_active
- `DELETE /api/kpis/{id}` — HR only; sets is_active=false (soft-delete, since scores reference it)

**Review cycles (HR admin only)**
- `GET /api/cycles` — list all
- `POST /api/cycles` — create a draft cycle
- `POST /api/cycles/{id}/assign` — auto-populate assignments from `employees.manager_id`; optional overrides
- `POST /api/cycles/{id}/open` — status → open
- `POST /api/cycles/{id}/close` — status → closed (scores become read-only)

**Reviews (reviewer + subject visibility)**
- `GET /api/reviews/mine` — assignments where I am the reviewer, current open cycles
- `GET /api/reviews/{assignment_id}` — full assignment + all scores
- `PUT /api/reviews/{assignment_id}/scores/{kpi_id}` — upsert one score
- `POST /api/reviews/{assignment_id}/submit` — sets status=submitted, submitted_at=now() (idempotent per assignment)

**Dashboard (JWT required)**
- `GET /api/dashboard/cycle/{id}` — HR view: completion %, score distribution, per-team averages

**Health**
- `GET /health` — liveness
- `GET /health/db` — DB round-trip

That's ~24 endpoints. Well within one-developer scope, and each one is small.

---

## 7. Auth design

Own auth. No third-party IDP.

### 7.1 Password storage

`Argon2id` via `passlib[argon2]` (or `argon2-cffi` directly). Parameters: `time_cost=3, memory_cost=64MiB, parallelism=1` — 2026 sensible default. Never store plaintext, never store SHA-anything.

### 7.2 Token model

- **Access token**: short-lived JWT (15 min). Signed with **HS256** and a strong random secret (`JWT_SECRET` in `.env`). Contains `sub=user_id`, `role`, `exp`, `iat`. Sent in `Authorization: Bearer <token>` header.
- **Refresh token**: opaque random 32-byte string. Server stores `sha256(token)` in `refresh_tokens` table. Sent in an `httpOnly; Secure; SameSite=lax` cookie. Rotated on every use (old one revoked, new one issued).

**Why this shape?**
- httpOnly cookie for refresh = XSS can't steal it
- Access token in memory (React state, not localStorage) = XSS can steal one 15-minute token but nothing durable
- Server-side refresh registry = logout, force-logout-everywhere, and detected replay are possible

### 7.3 Invitation flow (admin-only account creation)

```
1. HR admin: POST /api/users/invite {email, role, initial_employee: {...}}
2. Backend:
     - creates users row (password_hash NULL, is_active=false until accept)
     - creates employees row linked to user
     - generates raw token (32 random bytes, base64url-encoded)
     - stores sha256(token) in invitations table
     - emails: https://app.example.com/accept-invite?token=<raw>
3. Invitee clicks the link → AcceptInvite page
4. Frontend: POST /api/auth/accept-invite {token, full_name, password}
5. Backend:
     - looks up invitation by sha256(token)
     - verifies not consumed, not expired
     - updates users.password_hash, users.is_active=true
     - marks invitation.accepted_at = now()
     - returns access + refresh, logs them in
6. User lands on dashboard
```

### 7.4 Password reset flow

Same shape as invitations but shorter TTL (1 hour) and uses the `password_resets` table.

`POST /api/auth/forgot-password` **always** returns 202, even if the email doesn't exist — this prevents attackers from enumerating valid emails.

### 7.5 Backend auth dependency

```python
# app/auth/deps.py — sketch
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_session),
) -> User:
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = await db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return user

def require_role(*roles: str):
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Forbidden")
        return user
    return _check
```

Usage:

```python
@router.post("/kpis")
async def create_kpi(payload: KpiIn, user: User = Depends(require_role("hr_admin"))):
    ...
```

### 7.6 CORS

Set `CORS_ORIGINS` allowlist in `.env`. In dev: `http://localhost:5173`. In prod: the deployed frontend origin. `allow_credentials=True` (needed for the refresh cookie).

---

## 8. Local development

### 8.1 One-time system setup

- **Python 3.12+**
- **Node 20+** and **npm 10+**
- **PostgreSQL 16** — pick one:
  - **Native install** (Windows: [postgresql.org/download/windows](https://www.postgresql.org/download/windows/); macOS: `brew install postgresql@16`; Linux: `apt install postgresql-16`)
  - **One Docker container** (`docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=hrm -e POSTGRES_USER=hrm -e POSTGRES_DB=hrm --name hrm-db postgres:16-alpine`) — only DB in Docker, not the app
  - **Managed** (Neon free tier — no local install; harder for offline dev)
- **uv** for Python: `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 8.2 Clone & first run

```bash
git clone <repo>
cd hrm

# ---------- Backend ----------
cd backend
cp .env.example .env      # then fill DATABASE_URL, JWT_SECRET, RESEND_API_KEY
uv sync                   # creates .venv/, installs deps from uv.lock
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
# → http://localhost:8000/docs

# ---------- Frontend (new terminal) ----------
cd ../frontend
cp .env.example .env      # VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev
# → http://localhost:5173
```

### 8.3 Backend `.env.example`

```
# Postgres
DATABASE_URL=postgresql://hrm:hrm@localhost:5432/hrm

# Auth
JWT_SECRET=change-me-to-a-random-64-char-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_TTL_MINUTES=15
REFRESH_TOKEN_TTL_DAYS=30

# CORS
CORS_ORIGINS=["http://localhost:5173"]

# Cookies (dev vs prod)
COOKIE_SECURE=false                # true in prod (HTTPS)
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=

# Email (Resend, Postmark, or SMTP)
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_...
EMAIL_FROM=HRM <noreply@company.com>
APP_BASE_URL=http://localhost:5173
```

### 8.4 Frontend `.env.example`

```
VITE_API_BASE_URL=http://localhost:8000
```

### 8.5 Generate a strong JWT_SECRET

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 8.6 Everyday commands

Backend:
```bash
uv run uvicorn app.main:app --reload   # dev server
uv run pytest                           # tests
uv run ruff check .                     # lint
uv run alembic revision --autogenerate -m "add x"
uv run alembic upgrade head
uv run alembic downgrade -1
```

Frontend:
```bash
npm run dev
npm run build
npm run typecheck
npm run lint
```

---

## 9. Deployment (no Docker)

### 9.1 The topology

```
       ┌──────────────────────────────┐
       │      User's browser          │
       └────────────┬─────────────────┘
                    │ HTTPS
      ┌─────────────┴──────────────┐
      │  Frontend  (Vite static)   │
      │  Vercel                    │
      │  - vercel.com auto-builds  │
      │    on push to main         │
      └─────────────┬──────────────┘
                    │ fetch(VITE_API_BASE_URL, credentials: 'include')
                    │ Authorization: Bearer <JWT>
      ┌─────────────┴──────────────┐
      │  Backend  (FastAPI)        │
      │  Render / Fly / Railway    │
      │  - build cmd: uv sync      │
      │  - start cmd: uvicorn      │
      │    app.main:app --host 0   │
      └─────────────┬──────────────┘
                    │ asyncpg over TLS
      ┌─────────────┴──────────────┐
      │  PostgreSQL 16             │
      │  Neon / Render PG / Fly PG │
      └────────────────────────────┘
```

### 9.2 Vercel (frontend)

- Import the repo
- Root directory: `frontend/`
- Framework preset: Vite
- Env vars: `VITE_API_BASE_URL=https://api.yourcompany.com`
- Push to main → deploys

### 9.3 Render (backend — easiest option)

Add a `render.yaml` at repo root:

```yaml
services:
  - type: web
    name: hrm-backend
    runtime: python
    rootDir: backend
    buildCommand: pip install uv && uv sync --frozen
    startCommand: uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: hrm-postgres
          property: connectionString
      - key: JWT_SECRET
        generateValue: true
      - key: CORS_ORIGINS
        value: '["https://app.yourcompany.com"]'
      - key: COOKIE_SECURE
        value: "true"
      - key: RESEND_API_KEY
        sync: false          # add via dashboard
    autoDeploy: true

databases:
  - name: hrm-postgres
    plan: free
    postgresMajorVersion: "16"
```

Push to main → Render builds and deploys.

### 9.4 Fly.io (alternative)

Fly requires a Dockerfile in practice for Python apps, so it slightly bends the "no Docker" rule. But: a **6-line Dockerfile** is enough (`python:3.12-slim`, `uv sync`, `CMD uvicorn ...`), and Fly only uses it — you don't have to run Docker locally.

### 9.5 Custom domain + HTTPS

Both Vercel and Render issue free TLS certs. Point `app.yourcompany.com` at Vercel and `api.yourcompany.com` at Render via CNAME. Update `CORS_ORIGINS` and `APP_BASE_URL` accordingly.

### 9.6 Applying migrations in production

Render runs Alembic once on each deploy via a `preDeployCommand`:

```yaml
    preDeployCommand: uv run alembic upgrade head
```

For Fly: run `fly ssh console -C "cd /app && uv run alembic upgrade head"` after deploy, or as a `release_command` in `fly.toml`.

---

## 10. Phase-by-phase build plan

Each phase ends with something demonstrable and testable. Total: ~2–3 focused weeks by one dev.

### Phase 0 — Foundation (½ day)

- `git init`, `.gitignore`, initial commit, push to GitHub
- Create empty `backend/` and `frontend/` directories
- Add `README.md` with quickstart

### Phase 1 — Auth skeleton (2 days)

**Backend:**
- `uv init` + add deps: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`, `passlib[argon2]`, `pyjwt[crypto]`, `httpx`, `resend`
- Author `app/main.py` with `/health`
- Author `app/db.py`, `app/config.py`
- Author models: `User`, `Invitation`, `PasswordReset`, `RefreshToken`
- Alembic 0001: schema for above 4 tables + enums + trigger
- Author `app/auth/passwords.py`, `app/auth/tokens.py`, `app/auth/deps.py`, `app/auth/email.py`
- Author `app/routers/auth.py`: `/login`, `/refresh`, `/logout`, `/forgot-password`, `/reset-password`, `/accept-invite`
- Author `app/routers/users.py`: `/me`, `/users`, `/users/invite`

**Frontend:**
- Vite React-TS template
- Tailwind installed
- `apiClient.ts` with auto-refresh interceptor
- `AuthProvider`, `useAuth`, `ProtectedRoute`
- Pages: `Login`, `AcceptInvite`, `ForgotPassword`, `ResetPassword`
- Route table + basic Layout

**Test:**
- pytest: register admin (via seed script), invite user, accept, login, refresh, logout, reset password
- Manual: end-to-end in browser, dev mail preview

### Phase 2 — Employee directory (1 day)

**Backend:**
- Add `Employee` model + alembic 0002
- `app/routers/employees.py`: list, get, patch, get-by-id-with-reviews (stub for reviews list)
- Seed one HR admin user

**Frontend:**
- `Employees.tsx` (list + create/edit modal)
- `EmployeeProfile.tsx` (single employee)
- Layout nav: Dashboard | Employees | (KPIs / Cycles for HR)

**Test:**
- pytest for CRUD + role checks
- Manual: HR creates employees, employee sees only own profile

### Phase 3 — KPI catalog (½ day)

- `Kpi` model + alembic 0003
- `app/routers/kpis.py`
- `Kpis.tsx` (HR-only page)
- Seed a starter catalog (12 KPIs across 6 categories) via alembic data migration

### Phase 4 — Review cycles & assignments (1 day)

- `ReviewCycle`, `ReviewAssignment` models + alembic 0004
- `app/routers/reviews.py` — cycle CRUD, open/close, auto-assign from manager_id
- `ReviewCycles.tsx` (HR-only)
- Test: create cycle → assign → open → close cycle → assignments locked

### Phase 5 — Review flow (2 days)

- `ReviewScore` model + alembic 0005
- Score CRUD endpoints
- `DoReview.tsx` — reviewer-facing form (list assigned employees, click one, score each KPI + comment, submit)
- Constraint: can only edit while cycle status = 'open' AND assignment.status != 'submitted'
- Test: full round-trip — HR creates cycle, opens it, manager fills in scores, submits, HR sees results

### Phase 6 — Dashboard + polish (1 day)

- `Dashboard.tsx` for HR: completion % per cycle, average score per team, distribution histogram (Recharts)
- Employee dashboard: their own past reviews
- `SecuritySettings.tsx`: change password

### Phase 7 — Deploy (½ day)

- Push to GitHub
- Set up Neon Postgres + copy connection string
- Deploy backend to Render (or Fly) using `render.yaml`
- Deploy frontend to Vercel
- Configure `VITE_API_BASE_URL` and `CORS_ORIGINS`
- Verify via a real invite email to your own address
- Set up GitHub Actions for CI (lint + test on PR)

### Phase 8 — Optional hardening (1–2 days, when needed)

Do only if the team asks:
- Rate limiting (`slowapi`)
- Structured logging + Sentry
- Basic Playwright smoke test in CI
- Audit log table for admin actions
- Optional TOTP MFA for hr_admin users

---

## 11. Bootstrap checklist — what to create in what order

Follow this to go from empty folder to running app.

**Backend, in order:**

1. `backend/pyproject.toml` — with the deps from Phase 1
2. `backend/.python-version` — `3.12`
3. `backend/.env.example` — from §8.3
4. `backend/app/__init__.py` (empty)
5. `backend/app/config.py` — pydantic-settings Settings class reading `.env`
6. `backend/app/db.py` — async engine, `async_sessionmaker`, `Base = DeclarativeBase`, `get_session()` dep
7. `backend/app/models/_base.py` — mixins (TimestampMixin), enum type declarations
8. `backend/app/models/users.py` — User, Invitation, PasswordReset, RefreshToken
9. `backend/app/models/__init__.py` — re-export all
10. `backend/alembic.ini` — sqlalchemy.url blank
11. `backend/alembic/env.py` — async-aware, imports `app.models`
12. `backend/alembic/script.py.mako`
13. `uv sync` — creates `.venv/` and `uv.lock`
14. `uv run alembic revision --autogenerate -m "initial schema"` — becomes 0001
15. Hand-tune 0001 to add `set_updated_at()` trigger + per-table triggers + explicit DROP TYPE in downgrade
16. `uv run alembic upgrade head` — schema applied
17. `backend/app/auth/passwords.py` — `hash_password()`, `verify_password()`
18. `backend/app/auth/tokens.py` — `create_access_token()`, `decode_access_token()`, refresh token helpers
19. `backend/app/auth/email.py` — `send_invite_email()`, `send_reset_email()` via Resend SDK
20. `backend/app/auth/deps.py` — `get_current_user`, `require_role`
21. `backend/app/routers/auth.py`
22. `backend/app/routers/users.py`
23. `backend/app/schemas/*.py` — Pydantic request + response models
24. `backend/app/main.py` — FastAPI app, CORS middleware, mount routers
25. Seed script: `backend/scripts/create_hr_admin.py` — CLI that creates the first hr_admin
26. `backend/tests/conftest.py` — PG testcontainer + JWT test helper
27. Tests for each router
28. Then subsequent phases add: employees.py, kpis.py, reviews.py, dashboard.py — same pattern

**Frontend, in order:**

1. `npm create vite@latest frontend -- --template react-ts`
2. `cd frontend && npm install` (react-router, tailwind, autoprefixer, postcss, @tanstack/react-query optional)
3. `npx tailwindcss init -p`
4. `frontend/tailwind.config.js` + `frontend/src/index.css` + Tailwind directives
5. `frontend/.env.example` — `VITE_API_BASE_URL`
6. `frontend/src/lib/apiClient.ts` — fetch wrapper with `credentials: 'include'`, auto-refresh on 401
7. `frontend/src/auth/AuthProvider.tsx` + `useAuth.ts` + `ProtectedRoute.tsx`
8. `frontend/src/pages/Login.tsx`
9. `frontend/src/pages/AcceptInvite.tsx`
10. `frontend/src/pages/ForgotPassword.tsx`, `ResetPassword.tsx`
11. `frontend/src/App.tsx` — router table, wrapping AuthProvider
12. `frontend/src/components/Layout.tsx` — sidebar, top bar, logout button
13. Then phase-by-phase add: `Employees.tsx`, `EmployeeProfile.tsx`, `Kpis.tsx`, `ReviewCycles.tsx`, `DoReview.tsx`, `Dashboard.tsx`

---

## 12. Where the original codebase is helpful reference

The existing `hrm-migration/` codebase (or the original MOCHA export it came from) contains ~5,000 lines of solid product logic that's worth *reading* even if you're not porting it directly. The pieces most worth cribbing from:

- **Schema shape**: the `hrm-migration/backend/app/models/*.py` files show a working async SQLAlchemy 2.0 schema; the fresh build's schema is a subset of it
- **Alembic setup**: `hrm-migration/backend/alembic/env.py` is a battle-tested async env.py — copy it wholesale, just point at your new models
- **The `updated_at` trigger pattern**: `hrm-migration/backend/alembic/versions/0001_initial_schema.py` shows exactly how to install the PL/pgSQL function + per-table triggers
- **Enum downgrade gotcha**: same file's `downgrade()` explicitly drops all ENUM types; without this, downgrade+re-upgrade breaks with "type already exists"
- **RBAC matrix seed**: `hrm-migration/backend/alembic/versions/0002_seed_kpis_and_permissions.py` — even though the new build uses a simpler 3-role model (hr_admin / manager / employee) instead of the 4-role matrix, the seed pattern (module-level constants + bulk_insert) is exactly what you want for the fresh KPI seed
- **UI patterns**: the ~19 pages in `hrm-migration/frontend/src/react-app/pages/*` are visual references only — they use MOCHA auth hooks that don't apply, but the layouts, form flows, and Recharts usage are all reusable inspiration
- **API contract sketch**: the ~1,875-line worker at `hrm-migration/frontend/src/worker/index.ts` (Hono, but readable) shows what an HRM API surface looks like when the product grows past MVP — useful as "what we might add later"

**Do not** copy MOCHA auth code (`@getmocha/*`), the Cloudflare worker plumbing, the wrangler.json, or the docker-compose setup. All out of scope.

---

## 13. Trade-offs / decisions you might reconsider

Called out so you can push back:

| Decision | Why | When to reconsider |
|---|---|---|
| **Own auth, not Auth0 / Clerk / Supabase** | No IDP dependency, full control, tiny attack surface | If team grows past ~50 employees and someone asks about SSO |
| **HS256 JWT, not RS256/JWKS** | One secret to manage, no keypair rotation | If backend ever runs on multiple untrusted services that need to verify without the secret |
| **JWT access + refresh cookie hybrid** | Standard, secure, no session store | If you'd rather have opaque server-side sessions (simpler for pure browser apps) |
| **No Docker** | uv + npm are enough isolation | If you need multi-service compose (Redis, worker, etc.) |
| **PostgreSQL native install for local dev** | No container needed | If team members are on many OSes; then one Docker DB container |
| **3-role RBAC (hr_admin/manager/employee)** | MVP simplicity | When someone wants finer-grained perms (e.g. "HR specialist can see but not delete") |
| **No email templates library** | Plaintext + one HTML email is enough | When marketing wants branded templates |
| **Recharts** | Zero-config, sufficient | If the design system needs custom SVG charts |
| **Vite + React + TypeScript** | Fast, modern, universally supported | Not really; this is the answer |

---

## 14. Final notes

- Everything in this doc is **advisory, not prescriptive**. If a specific choice doesn't fit your context, pick the alternative and move on.
- The whole system is designed to be **one-person-buildable in ~2–3 weeks**. If it starts feeling bigger, cut scope from §2.2.
- The migration exercise in `hrm-migration/` proved that the schema shape and the review model are sound. The complexity there is entirely inherited from the MOCHA app's ambition (learning + surveys + 360 + goals + …). Cutting to the MVP surface in §2.1 makes this a fundamentally simpler project.
- The `HRM_TECHNICAL_DESIGN.md` file (this document) is intended to be self-contained. Copy it to a new folder alongside an empty git repo and follow §11 to bootstrap.

Good luck. Ship it.
