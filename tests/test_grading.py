"""Tests for the grading engine — the heart of Imtihan."""

from app.services.grading import grade_exam


def _questions():
    return [
        {
            "id": 1,
            "marks": 2.0,
            "options": [
                {"id": 101, "is_correct": True},
                {"id": 102, "is_correct": False},
            ],
        },
        {
            "id": 2,
            "marks": 1.0,
            "options": [
                {"id": 201, "is_correct": False},
                {"id": 202, "is_correct": True},
            ],
        },
        {
            "id": 3,
            "marks": 3.0,
            "options": [
                {"id": 301, "is_correct": True},
                {"id": 302, "is_correct": False},
            ],
        },
    ]


def test_all_correct_full_score():
    r = grade_exam(_questions(), {1: 101, 2: 202, 3: 301}, negative_marking=0.25)
    assert r.score == 6.0
    assert r.max_score == 6.0
    assert r.correct_count == 3
    assert r.wrong_count == 0
    assert r.skipped_count == 0
    assert r.percentage == 100.0


def test_wrong_answers_apply_negative_marking():
    # Q1 wrong (2 marks * 0.25 = -0.5), Q2 correct (+1), Q3 wrong (3 * 0.25 = -0.75)
    r = grade_exam(_questions(), {1: 102, 2: 202, 3: 302}, negative_marking=0.25)
    assert r.correct_count == 1
    assert r.wrong_count == 2
    assert r.score == round(max(0.0, 1.0 - 0.5 - 0.75), 4)  # clamps at 0
    assert r.score == 0.0


def test_negative_marking_never_below_zero():
    r = grade_exam(_questions(), {1: 102, 2: 201, 3: 302}, negative_marking=0.25)
    assert r.score == 0.0  # clamped, not negative
    assert r.skipped_count == 0


def test_skipped_questions_score_zero():
    r = grade_exam(_questions(), {1: 101}, negative_marking=0.25)
    assert r.score == 2.0
    assert r.skipped_count == 2
    assert r.correct_count == 1
    assert r.percentage == round(2.0 / 6.0 * 100, 2)


def test_missing_selection_treated_as_skipped():
    r = grade_exam(_questions(), {}, negative_marking=0.25)
    assert r.score == 0.0
    assert r.skipped_count == 3
    assert r.max_score == 6.0


def test_partial_marks_and_accuracy():
    r = grade_exam(_questions(), {1: 101, 2: 201}, negative_marking=0.5)
    # Q1 correct +2, Q2 wrong -0.5, Q3 skipped
    assert r.score == 1.5
    assert r.percentage == round(1.5 / 6.0 * 100, 2)


def test_no_negative_marking_when_zero():
    r = grade_exam(_questions(), {1: 102, 2: 202, 3: 302}, negative_marking=0.0)
    assert r.score == 1.0
    assert r.correct_count == 1
    assert r.wrong_count == 2


def test_grade_result_answer_details():
    r = grade_exam(_questions(), {1: 101, 2: 201}, negative_marking=0.25)
    by_q = {a.question_id: a for a in r.answers}
    assert by_q[1].is_correct is True
    assert by_q[1].earned == 2.0
    assert by_q[2].is_correct is False
    assert by_q[2].earned == -0.25
    assert by_q[3].skipped is True
    assert by_q[3].earned == 0.0
