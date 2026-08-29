"""End-to-end API tests: auth, exams, codes, submissions, analytics, permissions."""

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def _register(client, name, email, password, role):
    r = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password, "role": role},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create_exam(client, token, title="Physics Test 1"):
    payload = {
        "title": title,
        "subject": "Physics",
        "duration_minutes": 30,
        "negative_marking": 0.25,
        "questions": [
            {
                "text": "What is the SI unit of force?",
                "marks": 2.0,
                "options": [
                    {"text": "Newton", "is_correct": True},
                    {"text": "Joule", "is_correct": False},
                    {"text": "Watt", "is_correct": False},
                ],
            },
            {
                "text": "Speed of light?",
                "marks": 1.0,
                "options": [
                    {"text": "3e8 m/s", "is_correct": True},
                    {"text": "3e6 m/s", "is_correct": False},
                ],
            },
        ],
    }
    r = client.post("/api/exams", json=payload, headers=_auth_headers(token))
    assert r.status_code == 201, r.text
    return r.json()


# ---------- Auth ----------
def test_register_and_login(client):
    data = _register(client, "Ayesha", "ayesha@test.com", "password123", "student")
    assert "access_token" in data
    assert data["user"]["role"] == "student"

    r = client.post("/api/auth/login", json={"email": "ayesha@test.com", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "ayesha@test.com"


def test_register_duplicate_email_conflict(client):
    _register(client, "Ayesha", "dup@test.com", "password123", "student")
    r = client.post(
        "/api/auth/register",
        json={
            "name": "Other",
            "email": "dup@test.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert r.status_code == 409


def test_login_wrong_password(client):
    _register(client, "Ayesha", "wrong@test.com", "password123", "student")
    r = client.post("/api/auth/login", json={"email": "wrong@test.com", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_valid_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    r = client.get("/api/auth/me", headers=_auth_headers("garbage.token.here"))
    assert r.status_code == 401


def test_register_requires_min_password(client):
    r = client.post(
        "/api/auth/register",
        json={
            "name": "A",
            "email": "a@test.com",
            "password": "short",
            "role": "student",
        },
    )
    assert r.status_code == 422


# ---------- Exams (teacher-only) ----------
def test_student_cannot_create_exam(client):
    student = _register(client, "Sana", "s@test.com", "password123", "student")
    r = client.post(
        "/api/exams",
        json={
            "title": "Test Exam",
            "questions": [
                {
                    "text": "Q?",
                    "marks": 1,
                    "options": [
                        {"text": "A", "is_correct": True},
                        {"text": "B", "is_correct": False},
                    ],
                }
            ],
        },
        headers=_auth_headers(student["access_token"]),
    )
    assert r.status_code == 403


def test_teacher_creates_exam_with_questions(client):
    teacher = _register(client, "Sir", "sir@test.com", "password123", "teacher")
    exam = _create_exam(client, teacher["access_token"])
    assert exam["question_count"] == 2
    assert exam["title"] == "Physics Test 1"

    r = client.get("/api/exams", headers=_auth_headers(teacher["access_token"]))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_exam_question_needs_correct_option(client):
    teacher = _register(client, "Sir", "sir2@test.com", "password123", "teacher")
    r = client.post(
        "/api/exams",
        json={
            "title": "Bad Exam",
            "questions": [
                {
                    "text": "Q?",
                    "marks": 1,
                    "options": [
                        {"text": "A", "is_correct": False},
                        {"text": "B", "is_correct": False},
                    ],
                }
            ],
        },
        headers=_auth_headers(teacher["access_token"]),
    )
    assert r.status_code == 422


def test_teacher_cannot_see_others_exam(client):
    t1 = _register(client, "T1", "t1@test.com", "password123", "teacher")
    t2 = _register(client, "T2", "t2@test.com", "password123", "teacher")
    exam = _create_exam(client, t1["access_token"])
    r = client.get(f"/api/exams/{exam['id']}", headers=_auth_headers(t2["access_token"]))
    assert r.status_code == 404


def test_teacher_can_delete_own_exam(client):
    t1 = _register(client, "T1", "tdel@test.com", "password123", "teacher")
    exam = _create_exam(client, t1["access_token"])
    r = client.delete(f"/api/exams/{exam['id']}", headers=_auth_headers(t1["access_token"]))
    assert r.status_code == 204
    r = client.get(f"/api/exams/{exam['id']}", headers=_auth_headers(t1["access_token"]))
    assert r.status_code == 404


# ---------- Exam codes ----------
def test_generate_code_and_join(client):
    teacher = _register(client, "Sir", "codes@test.com", "password123", "teacher")
    exam = _create_exam(client, teacher["access_token"])
    r = client.post(
        f"/api/exams/{exam['id']}/codes",
        json={"max_uses": 50},
        headers=_auth_headers(teacher["access_token"]),
    )
    assert r.status_code == 201
    code = r.json()["code"]
    assert len(code) == 8

    student = _register(client, "St", "st@test.com", "password123", "student")
    r = client.post(
        "/api/exams/join",
        json={"code": code},
        headers=_auth_headers(student["access_token"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["question_count"] == 2
    # student must NOT see correct answers — options have no is_correct field
    for q in body["questions"]:
        for o in q["options"]:
            assert "is_correct" not in o


def test_join_with_invalid_code(client):
    student = _register(client, "St", "st2@test.com", "password123", "student")
    r = client.post(
        "/api/exams/join",
        json={"code": "NOPE1234"},
        headers=_auth_headers(student["access_token"]),
    )
    assert r.status_code == 404


# ---------- Submissions & grading ----------
def test_full_submission_flow_with_negative_marking(client):
    teacher = _register(client, "Sir", "flow@test.com", "password123", "teacher")
    exam = _create_exam(client, teacher["access_token"])
    r = client.post(
        f"/api/exams/{exam['id']}/codes",
        json={"max_uses": 100},
        headers=_auth_headers(teacher["access_token"]),
    )
    code = r.json()["code"]

    student = _register(client, "St", "flowst@test.com", "password123", "student")

    # join to discover question/option ids
    joined = client.post(
        "/api/exams/join",
        json={"code": code},
        headers=_auth_headers(student["access_token"]),
    ).json()
    q1, q2 = joined["questions"][0], joined["questions"][1]
    # q1 correct option is first (Newton), q2 correct is first (3e8) — but we pick WRONG for q2
    r = client.post(
        "/api/submissions",
        json={
            "code": code,
            "answers": [
                {
                    "question_id": q1["id"],
                    "option_id": q1["options"][0]["id"],
                },  # correct +2
                {
                    "question_id": q2["id"],
                    "option_id": q2["options"][1]["id"],
                },  # wrong -0.25
            ],
        },
        headers=_auth_headers(student["access_token"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["score"] == 1.75
    assert body["max_score"] == 3.0
    assert body["correct_count"] == 1
    assert body["wrong_count"] == 1
    assert body["skipped_count"] == 0
    assert body["percentage"] == round(1.75 / 3.0 * 100, 2)
    assert body["passed"] is True  # 58.3% >= 40 pass mark


def test_student_cannot_resubmit_same_exam(client):
    teacher = _register(client, "Sir", "resub@test.com", "password123", "teacher")
    exam = _create_exam(client, teacher["access_token"])
    code = client.post(
        f"/api/exams/{exam['id']}/codes",
        json={},
        headers=_auth_headers(teacher["access_token"]),
    ).json()["code"]
    student = _register(client, "St", "resubst@test.com", "password123", "student")
    joined = client.post(
        "/api/exams/join",
        json={"code": code},
        headers=_auth_headers(student["access_token"]),
    ).json()
    q1 = joined["questions"][0]

    payload = {
        "code": code,
        "answers": [{"question_id": q1["id"], "option_id": q1["options"][0]["id"]}],
    }
    r1 = client.post(
        "/api/submissions", json=payload, headers=_auth_headers(student["access_token"])
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/api/submissions", json=payload, headers=_auth_headers(student["access_token"])
    )
    assert r2.status_code == 409


def test_option_must_belong_to_question(client):
    teacher = _register(client, "Sir", "opt@test.com", "password123", "teacher")
    exam = _create_exam(client, teacher["access_token"])
    code = client.post(
        f"/api/exams/{exam['id']}/codes",
        json={},
        headers=_auth_headers(teacher["access_token"]),
    ).json()["code"]
    student = _register(client, "St", "optst@test.com", "password123", "student")
    joined = client.post(
        "/api/exams/join",
        json={"code": code},
        headers=_auth_headers(student["access_token"]),
    ).json()
    q1, q2 = joined["questions"][0], joined["questions"][1]

    # q1 answered with q2's option
    r = client.post(
        "/api/submissions",
        json={
            "code": code,
            "answers": [{"question_id": q1["id"], "option_id": q2["options"][0]["id"]}],
        },
        headers=_auth_headers(student["access_token"]),
    )
    assert r.status_code == 422


# ---------- Analytics ----------
def test_analytics_teacher_only_and_counts(client):
    teacher = _register(client, "Sir", "an@test.com", "password123", "teacher")
    exam = _create_exam(client, teacher["access_token"])
    code = client.post(
        f"/api/exams/{exam['id']}/codes",
        json={},
        headers=_auth_headers(teacher["access_token"]),
    ).json()["code"]

    student = _register(client, "St", "anst@test.com", "password123", "student")
    joined = client.post(
        "/api/exams/join",
        json={"code": code},
        headers=_auth_headers(student["access_token"]),
    ).json()
    q1, q2 = joined["questions"][0], joined["questions"][1]
    client.post(
        "/api/submissions",
        json={
            "code": code,
            "answers": [
                {"question_id": q1["id"], "option_id": q1["options"][0]["id"]},
                {"question_id": q2["id"], "option_id": q2["options"][0]["id"]},
            ],
        },
        headers=_auth_headers(student["access_token"]),
    )

    # student blocked
    r = client.get(
        f"/api/analytics/exam/{exam['id']}",
        headers=_auth_headers(student["access_token"]),
    )
    assert r.status_code == 403

    # teacher sees analytics
    r = client.get(
        f"/api/analytics/exam/{exam['id']}",
        headers=_auth_headers(teacher["access_token"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_submissions"] == 1
    assert body["highest_score"] == 3.0
    assert len(body["question_stats"]) == 2
    q1_stat = body["question_stats"][0]
    assert q1_stat["attempts"] == 1
    assert q1_stat["correct"] == 1
    assert q1_stat["accuracy"] == 100.0


def test_analytics_empty_exam(client):
    teacher = _register(client, "Sir", "an2@test.com", "password123", "teacher")
    exam = _create_exam(client, teacher["access_token"])
    r = client.get(
        f"/api/analytics/exam/{exam['id']}",
        headers=_auth_headers(teacher["access_token"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_submissions"] == 0
    assert body["question_stats"] == []


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
