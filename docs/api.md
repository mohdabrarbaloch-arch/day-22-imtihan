# API Reference

Base URL: `http://localhost:8000` (or your deployed origin). All endpoints return JSON. Interactive docs at `/docs`.

Auth endpoints return a `TokenOut` with `access_token` — send it as `Authorization: Bearer <token>`.

## Health

### `GET /api/health`
- 200 `{"status": "ok", "app": "Imtihan", "version": "1.0.0"}`

## Auth

### `POST /api/auth/register`
Rate limited: 5/min.
```json
{ "name": "Ayesha Khan", "email": "ayesha@tuition.pk", "password": "secret123", "role": "teacher" }
```
- 201 → `{ "access_token": "...", "token_type": "bearer", "user": {...} }`
- 409 email already registered · 422 validation
- `role` must be `teacher` or `student`; password ≥ 8 chars.

### `POST /api/auth/login`
Rate limited: 10/min.
```json
{ "email": "ayesha@tuition.pk", "password": "secret123" }
```
- 200 → same shape as register · 401 invalid credentials

### `GET /api/auth/me`
- 200 → `UserOut` · 401 invalid/missing token

## Exams (teacher)

### `POST /api/exams`
Create an exam. Teacher only (403 for students). Body:
```json
{
  "title": "Physics Test 1",
  "subject": "Physics",
  "description": "Chapter 1–3",
  "duration_minutes": 30,
  "negative_marking": 0.25,
  "questions": [
    { "text": "SI unit of force?", "marks": 2.0, "options": [
        { "text": "Newton", "is_correct": true },
        { "text": "Joule", "is_correct": false }
    ]}
  ]
}
```
- 201 → `ExamOut` (with `question_count`) · 422 if a question has no correct option

### `GET /api/exams`
- 200 → list of `ExamOut`. Teachers: own exams. Students: exams with an active code.

### `GET /api/exams/{exam_id}`
- 200 → `ExamDetailOut`. Teacher: full metadata (no correct answers exposed). Student: metadata only (questions come via join). Foreign/unknown → 404.

### `DELETE /api/exams/{exam_id}`
- 204 · Teacher only, own exam only.

## Exam codes

### `POST /api/exams/{exam_id}/codes`
Teacher only. Body: `{ "max_uses": 100, "ttl_days": 30 }` (both optional).
- 201 → `{ "id": 3, "exam_id": 1, "code": "K7M2P9QX", "max_uses": 100, "used_count": 0, "created_at": "...", "expires_at": "..." }`

### `GET /api/exams/{exam_id}/codes`
- 200 → list of codes for the exam (teacher only).

### `POST /api/exams/join`
Student only. Body: `{ "code": "K7M2P9QX" }` (case-insensitive).
- 200 → `ExamDetailOut` **with questions but no correct answers**
- 404 invalid/expired/exhausted code

## Submissions (student)

### `POST /api/submissions`
Rate limited: 10/min. Student only (403 teacher). Body:
```json
{
  "code": "K7M2P9QX",
  "answers": [
    { "question_id": 1, "option_id": 101 },
    { "question_id": 2, "option_id": null }
  ]
}
```
- 201 → `SubmissionResult`: score, max_score, correct/wrong/skipped counts, percentage, passed (≥40%), per-answer breakdown
- 404 invalid code · 409 already submitted this exam · 422 unknown question/option or option not belonging to question

### `GET /api/submissions/my`
- 200 → the student's submission history (exam title, score, percentage).

### `GET /api/submissions/exam/{exam_id}`
- 200 → all submissions for an exam (teacher only, own exam).

## Analytics (teacher)

### `GET /api/analytics/exam/{exam_id}`
- 200 → `ExamAnalytics`:
```json
{
  "exam_id": 1, "exam_title": "Physics Test 1",
  "total_submissions": 24, "average_score": 7.2, "highest_score": 10.0, "lowest_score": 1.5,
  "pass_rate": 66.7, "pass_percentage": 40.0,
  "question_stats": [
    { "question_id": 1, "text": "SI unit of force?", "marks": 2.0,
      "attempts": 24, "correct": 20, "wrong": 3, "skipped": 1, "accuracy": 83.3 }
  ]
}
```
- 403 student · 404 foreign/unknown exam

### `GET /api/analytics/overview`
- 200 → `{ "exam_count": 3, "submission_count": 87, "average_percentage": 61.4 }` (teacher only)

## Error format

All errors: `{ "detail": "human-readable message" }` (422 validation errors use FastAPI's standard detail array).
