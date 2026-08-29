# Setup Guide

## Prerequisites

- Python 3.11+
- (Optional) Docker + Docker Compose
- (Optional) A PostgreSQL 16 instance

## Option A — Local development (SQLite)

```bash
git clone https://github.com/mohdabrarbaloch-arch/day-22-imtihan
cd day-22-imtihan

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env

uvicorn app.main:app --reload --port 8000
```

- App + SPA: http://localhost:8000
- API docs: http://localhost:8000/docs

The SQLite database file (`imtihan.db`) is created automatically on startup.

## Option B — Docker Compose (PostgreSQL)

```bash
docker compose up --build
```

- App + UI: http://localhost:8000
- PostgreSQL runs in a container on port 5432.
- The compose file sets `DATABASE_URL=postgresql+psycopg2://imtihan:imtihan@db:5432/imtihan` automatically.

To tear down: `docker compose down -v`

## Option C — Vercel (serverless)

1. Push the repo to GitHub.
2. Import the repo at https://vercel.com/new.
3. Framework preset: **Other**. Build command: empty. Output directory: empty.
4. Add environment variables: `JWT_SECRET` (required), `DATABASE_URL` (use a hosted PostgreSQL — e.g. Neon/Supabase — serverless filesystems are ephemeral), `ALLOWED_ORIGINS`.
5. Deploy. `vercel.json` routes `/(api.*)` to the FastAPI serverless function (`api/index.py`); static assets are served from `frontend/` at `/`.

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | ✅ | `sqlite:///./imtihan.db` | SQLite or PostgreSQL connection string |
| `JWT_SECRET` | ✅ (prod) | `change-me...` | **Must change in production** — `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | `1440` | JWT lifetime (24h) |
| `ALLOWED_ORIGINS` | — | `*` | Comma-separated CORS origins |
| `RATE_LIMIT_REGISTER` | — | `5/minute` | SlowAPI limit |
| `RATE_LIMIT_LOGIN` | — | `10/minute` | SlowAPI limit |
| `RATE_LIMIT_SUBMIT` | — | `10/minute` | SlowAPI limit |
| `EXAM_CODE_TTL_DAYS` | — | `30` | Default join-code expiry |

## Troubleshooting

- **`No module named pydantic_settings`** → `pip install -r requirements.txt` fully.
- **Port already in use** → `uvicorn app.main:app --port 8001`.
- **Rate limited during testing** → raise limits in `.env` (tests already use high limits).
- **SQLite datetime comparison errors** → code handles naive vs aware UTC datetimes automatically.
