# Deployment & DevOps Handover — Zilla Clinicals HRM

This document is the operational handover for deploying and running the HRM app.
It assumes the reader owns infrastructure, not the app code. For architecture and
local dev, see [README.md](README.md) and [HRM_TECHNICAL_DESIGN.md](HRM_TECHNICAL_DESIGN.md).

## 1. What this is

- **Backend**: FastAPI (Python 3.12, `uv`), SQLAlchemy 2.0 async on PostgreSQL 16,
  Alembic migrations. Own auth (Argon2id passwords, JWT access token + rotating
  refresh token in an httpOnly cookie, optional TOTP 2FA). Stateless app process —
  all state is in Postgres, so it scales horizontally behind a load balancer.
- **Frontend**: React 19 + Vite static build (`frontend/dist`), served as static
  assets. Talks to the backend over HTTPS with `credentials: include`.
- **No app Docker required.** Postgres is the only stateful dependency.

## 2. Architecture at a glance

```
[ Browser ] --HTTPS--> [ Static frontend (Vercel/S3/CDN) ]
      |
      +----HTTPS (cookies)----> [ FastAPI (Render/VM/container) ] --> [ PostgreSQL 16 ]
```

The frontend and API are separate origins, so the refresh cookie must be
`SameSite=None; Secure` in production and `CORS_ORIGINS` must list the exact
frontend origin. Both are already wired in `render.yaml`.

## 3. Prerequisites

- PostgreSQL 16 (managed is fine — Render/Neon/RDS). A `postgresql://…` URL is
  auto-upgraded to the asyncpg driver in `app/config.py`; no manual change needed.
- Python 3.12 + `uv` on the backend host (or use the provided `render.yaml`).
- Node 20+ to build the frontend once.

## 4. Environment variables (backend)

Copy `backend/.env.example`. **Production-critical** values:

| Variable | Prod value | Notes |
|---|---|---|
| `ENV` | `production` | Turns on the startup safety guard (see §5). |
| `DATABASE_URL` | managed PG URL | `postgresql://…` accepted; auto-driver-swapped. |
| `JWT_SECRET` | 48+ random chars | `python -c "import secrets; print(secrets.token_urlsafe(48))"`. **Never** the placeholder. |
| `COOKIE_SECURE` | `true` | Required under HTTPS; guard refuses to boot if false. |
| `COOKIE_SAMESITE` | `none` | Needed because frontend/API are cross-site. |
| `CORS_ORIGINS` | `["https://<frontend-domain>"]` | JSON array, exact origins only. |
| `APP_BASE_URL` | `https://<frontend-domain>` | Used to build invite/reset links. |
| `ACCESS_TOKEN_TTL_MINUTES` | `15` (default) | Short-lived access token. |
| `REFRESH_TOKEN_TTL_DAYS` | `30` (default) | Rotating refresh token lifetime. |
| `EMAIL_PROVIDER` | `console` for now → `resend` later | See §8. |
| `RESEND_API_KEY` | set in dashboard | Only when `EMAIL_PROVIDER=resend`. |

Frontend build var: `VITE_API_BASE_URL=https://<api-domain>`.

## 5. Startup safety guard (built in)

When `ENV=production`, the app **fails to start** (raises at config load) if:
- `JWT_SECRET` is the placeholder or shorter than 32 chars, or
- `COOKIE_SECURE` is not `true`.

This is intentional — it prevents shipping forgeable tokens or cookies sent over
plain HTTP. If the process won't boot, read the error; it names the exact problem.

## 6. First deploy — step by step

1. **Provision Postgres** and set `DATABASE_URL`.
2. **Set all env vars** from §4 (`ENV=production`, strong `JWT_SECRET`, etc.).
3. **Run migrations**: `uv run alembic upgrade head`
   (Render runs this automatically as `preDeployCommand`.)
4. **Create the first admin** (interactive shell on the host):
   ```
   uv run python -m scripts.create_hr_admin \
     --email you@zillaclinicals.com --password '<strong-password>' --name 'Your Name'
   ```
   This script is idempotent — re-running it resets that admin's password.
5. **Start the API**: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   (add `--workers N` behind a process manager for concurrency; the app is stateless).
6. **Build & deploy the frontend**: from `frontend/`, `npm ci && npm run build`,
   publish `dist/` to your CDN/host with `VITE_API_BASE_URL` pointed at the API.
7. **Smoke test**: `GET /health` → 200; `GET /health/db` → confirms DB reachable;
   log in as the admin in the UI.

### Managed path (recommended, already configured)
- Backend + DB → **Render** via `render.yaml` (provisions PG, runs migrations,
  health-checks `/health`, generates `JWT_SECRET`). Set `RESEND_API_KEY` in the dashboard.
- Frontend → **Vercel**, root `frontend/` (see `frontend/vercel.json`). Set `VITE_API_BASE_URL`.
- Update `CORS_ORIGINS` / `APP_BASE_URL` in `render.yaml` to the real Vercel domain.

## 7. Migrations

- Apply: `uv run alembic upgrade head`. Latest revision: **0013**.
- Every schema change ships as a migration in `backend/alembic/versions/`; never
  edit the DB by hand. Migrations are transactional and have working `downgrade()`.
- Run `alembic upgrade head` on every deploy before starting new app processes.

## 8. Email (currently deferred)

Email (invites, password resets) is **not yet live** pending verification of the
`send.zillaclinicals.com` subdomain with Resend.

- **Until then**, set `EMAIL_PROVIDER=console`. In this mode the invite/reset
  **links are returned in the API response** (and surfaced in the admin UI), so
  HR can still onboard users by copying the link manually — no email needed.
- **When the subdomain is verified**: set `EMAIL_PROVIDER=resend`, `RESEND_API_KEY`,
  and a verified `EMAIL_FROM`. No code change required.

## 9. File storage

Employee photos and documents are stored **in Postgres** (BYTEA) today, behind a
swappable `BlobStorage` interface (`storage_backend=db`). Moving to S3/Cloudinary
later is a new adapter class + config flag — each stored document already records
its backend. **Back up Postgres accordingly** (blobs live in the DB for now).

Upload limits: `MAX_PHOTO_MB` (5), `MAX_DOCUMENT_MB` (15). The app streams and
caps uploads, **but you must also set a hard body limit at the reverse proxy**,
e.g. nginx `client_max_body_size 20m;`, so oversized bodies are rejected at the edge.

## 10. Security checklist (verify before go-live)

- [ ] `ENV=production`, strong `JWT_SECRET`, `COOKIE_SECURE=true`, `COOKIE_SAMESITE=none`.
- [ ] TLS terminates in front of the API; HTTP redirects to HTTPS.
- [ ] `CORS_ORIGINS` lists only the real frontend origin(s).
- [ ] Reverse-proxy request-body cap set (§9).
- [ ] Postgres backups enabled; `DATABASE_URL` uses least-privilege credentials.
- [ ] Rate limiting on (`RATE_LIMIT_ENABLED=true`, default). If behind a proxy,
      ensure the real client IP reaches the app (e.g. trust `X-Forwarded-For`) so
      limits are per-user, not per-proxy.
- [ ] First admin created with a strong password; rotate any dev password.
- [ ] Optional: enrol admin accounts in TOTP 2FA (Settings → Two-factor).

Built-in protections (no action needed): Argon2id password hashing, rotating +
revocable refresh tokens, capability-based RBAC, per-IP rate limits on
login/reset/invite, single-use TOTP codes and one-time recovery codes, and access
tokens that are type-scoped so a 2FA-challenge token can't be used as a session.

## 11. Reset to a clean slate

To wipe all demo/operational data and keep **one admin login + the KPI framework**:

```
cd backend
uv run python -m scripts.reset_clean_slate --email admin@zillaclinicals.com --yes
```

Removes all other users/employees, invitations, tokens, review cycles, goals,
surveys, uploaded documents, recovery codes, and audit logs. Preserves the KPI
categories/KPIs (company scoring config) and the named admin (password untouched;
its 2FA is reset). **Destructive and irreversible — target the right database.**

## 12. Health & observability

- `GET /health` — liveness (app up).
- `GET /health/db` — readiness (DB reachable).
- API docs at `/docs` (consider disabling or protecting in production).
- Logs go to stdout; ship them from your platform's log drain.

## 13. CI

- `.github/workflows/backend.yml` — ruff + pytest against a Postgres service.
- `.github/workflows/frontend.yml` — typecheck + build.
Both run on every relevant change; keep them green as the merge gate.
