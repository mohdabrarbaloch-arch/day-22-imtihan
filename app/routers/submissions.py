"""Submission routes — students take exams, get instant auto-graded results."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session, selectinload
from starlette.requests import Request

from app.core.database import get_db
from app.models.models import Answer, Exam, ExamCode, Question, Submission, User
from app.routers.auth import get_current_user
from app.schemas.schemas import (
    AnswerOut,
    SubmissionOut,
    SubmissionResult,
    SubmitIn,
)
from app.services.grading import grade_exam

router = APIRouter(prefix="/api/submissions", tags=["submissions"])
limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=SubmissionResult, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def submit_exam(
    payload: SubmitIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students only")

    code = db.query(ExamCode).filter(ExamCode.code == payload.code.strip().upper()).first()
    if code is None or code.is_expired or code.used_count >= code.max_uses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired exam code"
        )

    exam = (
        db.query(Exam)
        .options(selectinload(Exam.questions).selectinload(Question.options))
        .filter(Exam.id == code.exam_id)
        .first()
    )
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    # One submission per student per exam (retake not allowed in MVP)
    existing = (
        db.query(Submission)
        .filter(Submission.exam_id == exam.id, Submission.student_id == user.id)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted this exam",
        )

    # Map selected answers
    selected: dict[int, int | None] = {}
    valid_question_ids = {q.id for q in exam.questions}
    valid_option_ids = {o.id for q in exam.questions for o in q.options}
    for a in payload.answers:
        if a.question_id not in valid_question_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown question id {a.question_id}",
            )
        if a.option_id is not None and a.option_id not in valid_option_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown option id {a.option_id}",
            )
        selected[a.question_id] = a.option_id

    questions_for_grade = [
        {
            "id": q.id,
            "marks": q.marks,
            "options": [{"id": o.id, "is_correct": o.is_correct} for o in q.options],
        }
        for q in exam.questions
    ]

    result = grade_exam(questions_for_grade, selected, exam.negative_marking)

    # Option cross-check: make sure chosen option belongs to its question
    option_to_question = {o.id: q.id for q in exam.questions for o in q.options}

    submission = Submission(
        exam_id=exam.id,
        student_id=user.id,
        code_id=code.id,
        submitted_at=datetime.now(UTC),
        score=result.score,
        max_score=result.max_score,
        correct_count=result.correct_count,
        wrong_count=result.wrong_count,
        skipped_count=result.skipped_count,
    )
    db.add(submission)
    db.flush()

    for g in result.answers:
        # ensure the selected option is actually one of THIS question's options
        chosen = g.option_id
        if chosen is not None and option_to_question.get(chosen) != g.question_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Option does not belong to question",
            )
        db.add(
            Answer(
                submission_id=submission.id,
                question_id=g.question_id,
                option_id=chosen,
                is_correct=g.is_correct,
                earned=g.earned,
            )
        )

    # Consume the code
    code.used_count += 1
    db.commit()

    percentage = result.percentage
    return SubmissionResult(
        submission_id=submission.id,
        exam_id=exam.id,
        exam_title=exam.title,
        score=result.score,
        max_score=result.max_score,
        correct_count=result.correct_count,
        wrong_count=result.wrong_count,
        skipped_count=result.skipped_count,
        percentage=percentage,
        passed=percentage >= 40.0,
        submitted_at=submission.submitted_at,
        auto_submitted=False,
        answers=[
            AnswerOut(
                question_id=g.question_id,
                option_id=g.option_id,
                is_correct=g.is_correct,
                earned=g.earned,
            )
            for g in result.answers
        ],
    )


@router.get("/my", response_model=list[SubmissionOut])
def my_submissions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subs = (
        db.query(Submission)
        .options(selectinload(Submission.exam))
        .filter(Submission.student_id == user.id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    out = []
    for s in subs:
        pct = round(s.score / s.max_score * 100, 2) if s.max_score else 0.0
        out.append(
            SubmissionOut(
                id=s.id,
                exam_id=s.exam_id,
                exam_title=s.exam.title,
                student_name=user.name,
                score=s.score,
                max_score=s.max_score,
                percentage=pct,
                submitted_at=s.submitted_at,
                auto_submitted=s.auto_submitted,
            )
        )
    return out


@router.get("/exam/{exam_id}", response_model=list[SubmissionOut])
def exam_submissions(
    exam_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access required")
    exam = db.get(Exam, exam_id)
    if exam is None or exam.teacher_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    subs = (
        db.query(Submission)
        .options(selectinload(Submission.student))
        .filter(Submission.exam_id == exam.id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    out = []
    for s in subs:
        pct = round(s.score / s.max_score * 100, 2) if s.max_score else 0.0
        out.append(
            SubmissionOut(
                id=s.id,
                exam_id=s.exam_id,
                exam_title=exam.title,
                student_name=s.student.name,
                score=s.score,
                max_score=s.max_score,
                percentage=pct,
                submitted_at=s.submitted_at,
                auto_submitted=s.auto_submitted,
            )
        )
    return out
