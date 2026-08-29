"""Tests for security helpers — password hashing and JWT."""

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    h = hash_password("super-secret-123")
    assert h != "super-secret-123"
    assert verify_password("super-secret-123", h) is True
    assert verify_password("wrong-pass", h) is False


def test_hash_is_salted():
    h1 = hash_password("same-pass")
    h2 = hash_password("same-pass")
    assert h1 != h2
    assert verify_password("same-pass", h1) and verify_password("same-pass", h2)


def test_jwt_roundtrip():
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_jwt_invalid_token_returns_none():
    assert decode_access_token("not.a.jwt") is None


def test_jwt_tampered_returns_none():
    token = create_access_token(7)
    tampered = token[:-4] + "AAAA"
    assert decode_access_token(tampered) is None
