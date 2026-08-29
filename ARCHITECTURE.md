# Imtihan — Architecture

**Imtihan (امتحان)** is an online exam & quiz platform for tuition centers, coaching academies and schools. Teachers create exams, students join with a short code, submit, and get instant auto-graded results with negative marking. Teachers get per-exam and per-question analytics.

## System diagram

```
                         ┌─────────────────────────────────────────────┐
                         │              Browser (SPA)                 │
                         │   mobile-first dark UI · zero build step   │
                         └────────────────────────────────────────────┘
                                            │  REST (JSON)
                                            ▼
                         ┌───────────────────────────────────────────┐
                         │               FastAPI app                   │
                         │  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
                         │  │  auth    │ │  exams   │ │ submissions │  │
                         │  │ (JWT)    │ │ (CRUD)   │ │ (grading)   │  │
                         │  └──────────┘ └──────────┘ └─────────────┘  │
                         │  ┌──────────┐ ┌──────────────────────────┐  │
                         │  │analytics │ │ rate limits (SlowAPI)    │  │
                         │  └──────────┘ └──────────────────────────┘  │
                         └──────────────┬─────────────────────────────┘
                                        │ SQLAlchemy 2.0 ORM
                                        ▼
                         ┌─────────────────────────────────────────────┐
                         │  PostgreSQL 16 (prod) / SQLite (dev)       │
                         │  users · exams · questions · options       │
                         │  exam_codes · submissions · answers        │
                         └───────────────────────────────────────┘
```

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.115 · Python 3.11 · Pydantic v2 |
| ORM | SQLAlchemy 2.0 (typed `Mapped`/`mapped_column`) |
| Auth | JWT (HS256, 24h) + bcrypt (12 rounds) |
| Rate limiting | SlowAPI (register 5/min, login 10/min, submit 10/min) |
| Database | SQLite (dev, WAL) / PostgreSQL 16 (docker-compose) |
| Frontend | Vanilla JS SPA, mobile-first dark UI, no build step |
| Infra | Docker · docker-compose · Vercel-ready (`vercel.json` + `api/index.py`) |

## Data model

- **users** — id, name, email (unique), password_hash, role (`teacher` | `student`)
- **exams** — id, teacher_id, title, subject, description, duration_minutes, negative_marking (0–1 fraction), shuffle_questions
- **questions** — id, exam_id, text, marks, position
- **options** — id, question_id, text, is_correct, position (answers never leave the server; students only ever see option text)
- **exam_codes** — id, exam_id, code (8-char, unambiguous charset, unique), max_uses, used_count, expires_at (default 30 days)
- **submissions** — id, exam_id, student_id, code_id, started_at, submitted_at, score, max_score, correct/wrong/skipped counts
- **answers** — id, submission_id, question_id, option_id, is_correct, earned

## Key flows

### Exam creation (teacher)
1. Teacher registers with role `teacher`, logs in → JWT.
2. `POST /api/exams` with title, subject, duration, negative_marking and questions (each with ≥1 correct option — enforced by Pydantic validator).
3. `POST /api/exams/{id}/codes` → server generates an 8-char code (charset excludes `O/0/I/1`), with max_uses and 30-day expiry.
4. Teacher shares the code with students (WhatsApp, classroom, etc.).

### Taking an exam (student)
1. Student registers with role `student`, logs in.
2. `POST /api/exams/join` with the code → server validates code (exists, not expired, not exhausted) and returns the exam **without correct answers**.
3. `POST /api/submissions` with the code + selected options → server:
   - validates every question/option id belongs to the exam (option must belong to its question),
   - runs the pure grading engine (`app/services/grading.py`): correct `+marks`, wrong `−marks × negative_marking`, skipped `0`, total clamped at ≥ 0,
   - blocks duplicate submissions per student per exam (409),
   - increments the code's `used_count` atomically,
   - returns the full result card immediately.

### Analytics (teacher)
- `GET /api/analytics/exam/{id}` → total submissions, avg/highest/lowest score, pass rate (≥40%), and **per-question** breakdown (attempts, correct, wrong, skipped, accuracy %).
- `GET /api/analytics/overview` → counts across all of a teacher's exams.

## Security

- Passwords hashed with bcrypt(12); JWT HS256 with server-side secret from env only.
- Ownership checks everywhere: a teacher can only see/delete their own exams (foreign access → 404, no existence leak).
- Students never receive `is_correct` flags — correct answers stay server-side.
- Role gates: exam creation/codes/analytics are teacher-only (403).
- SlowAPI rate limits on register/login/submit; global 429 handler.
- CORS allow-list via env; Pydantic validation on every input.

## Scaling notes

- **Grading engine is pure** — it takes plain dicts and returns plain dataclasses. In a multi-worker deployment it can be called from any worker or moved to a task queue without changes.
- **SQLite → PostgreSQL**: only the connection string changes (`DATABASE_URL`). The ORM layer is engine-agnostic; `with_for_update` row locks can be added around code consumption for higher concurrency.
- **Horizontal scaling**: FastAPI is stateless (JWT auth) — add more uvicorn workers or containers behind a load balancer.
- **Vercel**: `vercel.json` routes `/(api.*)` to the FastAPI app via `api/index.py` (serverless ASGI); the SPA is served statically. SQLite files are ephemeral on serverless — use PostgreSQL for any long-lived deployment.

## Local dev

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Tests: `pytest tests/ -q` (37 tests).
