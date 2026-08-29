# Imtihan — امتحان

**Online exam & quiz platform for tuition centers, coaching academies and schools.**

Teachers build exams in minutes, students join with a short code, and everyone gets instant results — auto-graded with negative marking, zero paper, zero manual checking.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)
![Tests](https://img.shields.io/badge/tests-37%20passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue)
![Deploy](https://img.shields.io/badge/deploy-Vercel--ready-black?logo=vercel)

---

## Why Imtihan?

Running a tuition center means printing test papers, checking 40 answer sheets by hand, and re-explaining the same mistakes every week. Imtihan automates the whole loop:

- **Teachers** create an exam in a few minutes — add questions, set marks, pick negative marking.
- **Students** join with an 8-character code — no accounts to share, no links to lose.
- **Results appear instantly** — score, correct/wrong/skipped breakdown, pass/fail.
- **Teachers see analytics** — average score, pass rate, and which questions the whole class got wrong.

Built for Pakistani tuition centers first (that's why the name is Urdu), but it works for any classroom, coaching academy, or even corporate training.

## Features

- 📝 **Exam builder** — up to 200 questions per exam, 2–6 options each, per-question marks, duration limit
- 🎯 **Negative marking** — configurable per exam (e.g. −0.25 per wrong answer), total never goes below zero
- 🔑 **Join codes** — short unguessable codes (no `O/0/I/1`), max-uses + 30-day expiry, one code per class
- ⚡ **Instant auto-grading** — results in milliseconds, with per-answer breakdown
- 📊 **Teacher analytics** — average/highest/lowest score, pass rate, per-question accuracy (find the question the whole class failed)
- 🔐 **Secure by design** — students never see correct answers; teachers only see their own exams; bcrypt + JWT + rate limits
- 📱 **Mobile-first dark UI** — works great on a phone in class, no build step, served instantly

## Screenshots

*Screenshots are added to the repo release assets — see the [v1.0.0 release](https://github.com/mohdabrarbaloch-arch/day-22-imtihan/releases/tag/v1.0.0).*

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.115 · Python 3.11 · SQLAlchemy 2.0 · Pydantic v2 |
| Auth | JWT (HS256, 24h) · bcrypt (12 rounds) · SlowAPI rate limits |
| Database | SQLite (dev) · PostgreSQL 16 (docker-compose) |
| Frontend | Vanilla JS · mobile-first dark SPA · zero build step |
| Infra | Docker · docker-compose · Vercel-ready |

## Quick start (local)

```bash
git clone https://github.com/mohdabrarbaloch-arch/day-22-imtihan
cd day-22-imtihan
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# run the API
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** — the SPA is served from `/`. Swagger docs at **http://localhost:8000/docs**.

### Docker

```bash
docker compose up --build
# API + UI on http://localhost:8000
```

## Demo flow (2 minutes)

1. Register as a **teacher** (role: teacher) → create an exam with 2–3 questions → generate a join code.
2. Open a private window, register as a **student** (role: student) → join with the code → answer the questions.
3. Back in the teacher account → open the exam → **Analytics** tab → see the per-question breakdown.

## Running tests

```bash
pytest tests/ -q     # 37 tests
```

## API reference

See [docs/API.md](docs/API.md). Full interactive docs at `/docs` when running.

## Project structure

```
day-22-imtihan/
├── app/
│   ├── core/          # config, database, security
│   ├── models/        # SQLAlchemy models
│   ├── routers/       # auth, exams, submissions, analytics
│   ├── schemas/       # Pydantic v2 contracts
│   ├── services/      # grading engine, exam codes
│   └── main.py        # FastAPI app
├── frontend/          # SPA (index.html, style.css, app.js)
├── tests/             # 37 unit + API tests
├── docs/              # setup, usage, API reference
├── api/               # Vercel serverless entry
├── Dockerfile · docker-compose.yml · vercel.json
└── ARCHITECTURE.md
```

## Deployment

See [docs/SETUP.md](docs/SETUP.md) for Docker and Vercel instructions.

## License

MIT — see [LICENSE](LICENSE).

---

*Made for the tuition centers of Pakistan — one exam at a time.* 🇵🇰
