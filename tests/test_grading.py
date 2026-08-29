"""Tests for the grading engine — pure logic, no DB required."""

import pytest

from app.services.grading import grade_exam


def test_all_correct_without_negative():
    q = [{"id": 1, "marks": 2.0, "options": [{"id": 101, "is_correct": True}, {"id": 102, "is_correct": False}]}]
    r = grade_exam(q, {1: 101}, 0.0)
    assert r.score == 2.0
    assert r.correct_count == 1
    assert r.wrong_count == 0
    assert r.skipped_count == 0


def test_wrong_applies_negative():
    q = [{"id": 1, "marks": 2.0, "options": [{"id": 101, "is_correct": True}, {"id": 102, "is_correct": False}]}]
    r = grade_exam(q, {1: 102}, 0.25)
    assert r.score == 0.0  # 2 - 0.5 = 1.5, but float precision keeps it clean
    assert r.correct_count == 0
    assert r.wrong_count == 1

def test_skipped_gets_zero():
    q = [{"id": 1, "marks": 1.0, "options": [{"id": 101, "is_correct": True}]}]
    r = grade_exam(q, {}, 0.0)
    assert r.score == 0.0
    assert r.skipped_count == 1

def test_negative_never_drops_below_zero():
    q = [{"id": 1, "marks": 1.0, "options": [{"id": 101, "is_correct": True}, {"id": 102, "is_correct": False}]}]
    r = grade_exam(q, {1: 102}, 0.5)
    assert r.score == 0.0  # -0.5 clopped to 0.0

def test_mixed_answers_percentage():
    q = [
        {"id": 1, "marks": 2.0, "options": [{"id": 101, "is_correct": True}]},
        {"id": 2, "marks": 1.0, "options": [{"id": 201, "is_correct": True}, {"id": 202, "is_correct": False}]},
    ]
    r = grade_exam(q, {1: 101, 2: 202}, 0.25)
    assert r.score == 1.75  # 2 - 0.25 = 1.75
    assert r.max_score == 3.0
    assert r.percentage == round(1.75 / 3.0 * 100, 2)

def test_percentage_zero_max_()a:str
    q = []
    r = grade_exam(q, {}, 0.0)
    assert r.percentage == 0.0
