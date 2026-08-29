"""Analytics routes — teachers get per-exam and per-question breakdowns."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.models import Answer, Exam, Question, Submission, User
from app.routers.auth import get_current_user
from app.schemas.schemas import ExamAnalytics, QuestionStat

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/exam/{exam_id}", response_model=ExamAnalytics)
def exam_analytics(
    exam_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access required")

    exam = db.get(Exam, exam_id)
    if exam is None or exam.teacher_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    subs = db.query(Submission).filter(Submission.exam_id == exam.id).all()
    questions = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.exam_id == exam.id)
        .order_by(Question.position)
        .all()
    )

    total = len(subs)
    if total == 0:
        return ExamAnalytics(
            exam_id=exam.id,
            exam_title=exam.title,
            total_submissions=0,
            average_score=0.0,
            highest_score=0.0,
            lowest_score=0.0,
            pass_rate=0.0,
            pass_percentage=40.0,
            question_stats=[],
        )

    scores = [s.score for s in subs if s.score is not None]
    percentages = [s.score / s.max_score * 100 if s.max_score else 0.0 for s in subs]
    passed = sum(1 for p in percentages if p >= 40.0)

    # Per-question stats: iterate answers joined to submissions of this exam
    q_stats: list[QuestionStat] = []
    for q in questions:
        ans_rows = (
            db.query(Answer)
            .join(Submission, Answer.submission_id == Submission.id)
            .filter(
                Submission.exam_id == exam.id,
                Answer.question_id == q.id,
            )
            .all()
        )
        attempts = len(ans_rows)
        correct = sum(1 for a in ans_rows if a.is_correct)
        wrong = sum(1 for a in ans_rows if not a.is_correct and a.option_id is not None)
        skipped = sum(1 for a in ans_rows if a.option_id is None)
        accuracy = round(correct / attempts * 100, 1) if attempts else 0.0
        q_stats.append(
            QuestionStat(
                question_id=q.id,
                text=q.text[:120],
                marks=q.marks,
                attempts=attempts,
                correct=correct,
                wrong=wrong,
                skipped=skipped,
                accuracy=accuracy,
            )
        )

    return ExamAnalytics(
        exam_id=exam.id,
        exam_title=exam.title,
        total_submissions=total,
        average_score=round(sum(scores) / len(scores), 2) if scores else 0.0,
        highest_score=max(scores) if scores else 0.0,
        lowest_score=min(scores) if scores else 0.0,
        pass_rate=round(passed / total * 100, 1),
        pass_percentage=40.0,
        question_stats=q_stats,
    )


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Teacher dashboard overview — counts across all their exams."""
    if user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access required")

    exam_count = db.query(func.count(Exam.id)).filter(Exam.teacher_id == user.id).scalar() or 0
    sub_count = (
        db.query(func.count(Submission.id))
        .join(Exam, Submission.exam_id == Exam.id)
        .filter(Exam.teacher_id == user.id)
        .scalar()
        or 0
    )
    avg_pct = (
        db.query(func.avg(Submission.score * 1.0 / Submission.max_score * 100))
        .join(Exam, Submission.exam_id == Exam.id)
        .filter(Exam.teacher_id == user.id, Submission.max_score > 0)
        .scalar()
    )
    avg_pct = round(avg_pct, 1) if avg_pct is not None else 0.0

    return {
        "exam_count": exam_count,
        "submission_count": sub_count,
        "average_percentage": avg_pct,
    }
