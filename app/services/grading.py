"""The grading engine — pure logic, fully unit-tested.

Rules:
  - correct answer  -> +question.marks
  - wrong answer    -> -question.marks * negative_marking (never below 0 total)
  - skipped answer  -> 0
"""

from dataclasses import dataclass


@dataclass
class GradedAnswer:
    question_id: int
    option_id: int | None
    is_correct: bool
    earned: float
    skipped: bool


@dataclass
class GradeResult:
    score: float
    max_score: float
    correct_count: int
    wrong_count: int
    skipped_count: int
    answers: list[GradedAnswer]

    @property
    def percentage(self) -> float:
        if self.max_score <= 0:
            return 0.0
        return round(self.score / self.max_score * 100, 2)


def grade_exam(
    questions: list[dict],
    selected: dict[int, int | None],
    negative_marking: float = 0.0,
) -> GradeResult:
    """Grade a submission.

    questions: list of dicts with keys id, marks, and options (list of dicts
              with id, is_correct).
    selected: mapping question_id -> option_id (None / missing = skipped).
    """
    max_score = 0.0
    score = 0.0
    correct = 0
    wrong = 0
    skipped = 0
    graded: list[GradedAnswer] = []

    for q in questions:
        qid = q["id"]
        marks = float(q["marks"])
        max_score += marks
        chosen = selected.get(qid)

        if chosen is None:
            skipped += 1
            graded.append(GradedAnswer(qid, None, False, 0.0, True))
            continue

        correct_option_ids = {o["id"] for o in q["options"] if o["is_correct"]}
        if chosen in correct_option_ids:
            correct += 1
            score += marks
            graded.append(GradedAnswer(qid, chosen, True, marks, False))
        else:
            wrong += 1
            penalty = marks * float(negative_marking)
            score -= penalty
            graded.append(GradedAnswer(qid, chosen, False, -penalty, False))

    # Total never drops below zero
    score = max(0.0, round(score, 4))
    return GradeResult(
        score=score,
        max_score=round(max_score, 4),
        correct_count=correct,
        wrong_count=wrong,
        skipped_count=skipped,
        answers=graded,
    )
