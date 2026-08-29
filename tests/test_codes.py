"""Tests for exam code generation + expiry logic."""

from datetime import timedelta

from app.models.models import ExamCode, utcnow
from app.services.codes import generate_exam_code


def test_code_length_and_charset():
    for _ in range(50):
        code = generate_exam_code()
        assert len(code) == 8
        assert code.isalnum()
        assert not any(c in "OI01" for c in code)  # no confusing chars


def test_codes_are_unique_in_practice():
    codes = {generate_exam_code() for _ in range(200)}
    assert len(codes) == 200


def test_code_not_expired():
    c = ExamCode(
        code="TEST1234",
        max_uses=10,
        used_count=0,
        expires_at=utcnow() + timedelta(days=1),
    )
    assert c.is_expired is False
    assert c.can_use() is True


def test_code_expired_when_past():
    c = ExamCode(
        code="TEST1234",
        max_uses=10,
        used_count=0,
        expires_at=utcnow() - timedelta(minutes=1),
    )
    assert c.is_expired is True
    assert c.can_use() is False


def test_code_exhausted_when_max_uses_reached():
    c = ExamCode(
        code="TEST1234",
        max_uses=2,
        used_count=2,
        expires_at=utcnow() + timedelta(days=1),
    )
    assert c.can_use() is False


def test_code_never_expires_when_null():
    c = ExamCode(code="TEST1234", max_uses=5, used_count=0, expires_at=None)
    assert c.is_expired is False
    assert c.can_use() is True
