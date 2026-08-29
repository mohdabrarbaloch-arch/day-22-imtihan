"""Exam routes — teachers create/manage exams; students browse + join."""

from fastapi import APIRouter, Depends, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.models import Exam, ExamCode, Option, Question, User
from app.routers.auth import get_current_user
from app.schemas.schemas import (
    ExamCodeCreate,
    ExamCodeOut,
    ExamCreate,
    ExamDetailOut,
    ExamJoinIn,
    ExamOut,
)
from app.services.codes import generate_exam_code

router = APIRouter(prefix="/api/exams", tags=["exams"])
limiter = Limiter(key_func=get_remote_address)


def _require_teacher(user: User) -> None:
    if user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access required")


def _get_owned_exam(db: Session, exam_id: int, user: User) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None or exam.teacher_id != user.id:
        # 404 hides existence from other users
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


# ---------- Teacher: exam CRUD ----------
@router.post("", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
def create_exam(
    payload: ExamCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    exam = Exam(
        teacher_id=user.id,
        title=payload.title.strip(),
        subject=payload.subject.strip(),
        description=payload.description.strip(),
        duration_minutes=payload.duration_minutes,
        negative_marking=payload.negative_marking,
        shuffle_questions=payload.shuffle_questions,
    )
    db.add(exam)
    db.flush()  # get exam.id

    for pos, q in enumerate(payload.questions):
        question = Question(
            exam_id=exam.id,
            text=q.text.strip(),
            marks=q.marks,
            position=pos,
        )
        db.add(question)
        db.flush()
        for opos, o in enumerate(q.options):
            db.add(
                Option(
                    question_id=question.id,
                    text=o.text.strip(),
                    is_correct=o.is_correct,
                    position=opos,
                )
            )
    db.commit()
    db.refresh(exam)
    return _exam_out(exam)


@router.get("", response_model=list[ExamOut])
def list_my_exams(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Exam)
    if user.role == "teacher":
        query = query.filter(Exam.teacher_id == user.id)
    else:
        # students see exams that have at least one usable code
        query = query.join(ExamCode).filter(ExamCode.used_count < ExamCode.max_uses).distinct()
    exams = query.order_by(Exam.created_at.desc()).all()
    return [_exam_out(e) for e in exams]


def _exam_out(exam: Exam) -> ExamOut:
    return ExamOut(
        id=exam.id,
        title=exam.title,
        subject=exam.subject,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        negative_marking=exam.negative_marking,
        shuffle_questions=exam.shuffle_questions,
        created_at=exam.created_at,
        question_count=len(exam.questions),
    )


@router.get("/{exam_id}", response_model=ExamDetailOut)
def get_exam(exam_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    exam = (
        db.query(Exam)
        .options(selectinload(Exam.questions).selectinload(Question.options))
        .filter(Exam.id == exam_id)
        .first()
    )
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    # teachers: full detail (incl. correct answers). students: only via join code
    if user.role == "teacher":
        if exam.teacher_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
        return _exam_detail(exam, include_answers=False)

    # students get metadata only here; questions come via /join
    return _exam_detail(exam, include_questions=False)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _require_teacher(user)
    exam = _get_owned_exam(db, exam_id, user)
    db.delete(exam)
    db.commit()


# ---------- Teacher: exam codes ----------
@router.post("/{exam_id}/codes", response_model=ExamCodeOut, status_code=status.HTTP_201_CREATED)
def create_code(
    exam_id: int,
    payload: ExamCodeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    exam = _get_owned_exam(db, exam_id, user)
    code = ExamCode(
        exam_id=exam.id,
        code=generate_exam_code(),
        max_uses=payload.max_uses,
        expires_at=ExamCode.default_expiry() if payload.ttl_days is None else None,
    )
    if payload.ttl_days is not None:
        from datetime import timedelta

        code.expires_at = ExamCode.default_expiry() + timedelta(days=payload.ttl_days - 30)
    db.add(code)
    db.commit()
    db.refresh(code)
    return ExamCodeOut.model_validate(code)


@router.get("/{exam_id}/codes", response_model=list[ExamCodeOut])
def list_codes(exam_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_teacher(user)
    exam = _get_owned_exam(db, exam_id, user)
    codes = (
        db.query(ExamCode)
        .filter(ExamCode.exam_id == exam.id)
        .order_by(ExamCode.created_at.desc())
        .all()
    )
    return [ExamCodeOut.model_validate(c) for c in codes]


# ---------- Student: join with a code ----------
@router.post("/join", response_model=ExamDetailOut)
def join_exam(
    payload: ExamJoinIn,
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

    return _exam_detail(exam, include_answers=False, include_questions=True)


def _exam_detail(
    exam: Exam, include_questions: bool, include_answers: bool = False
) -> ExamDetailOut:
    questions = []
    qs = sorted(exam.questions, key=lambda q: q.position)
    if include_questions:
        for q in qs:
            opts = sorted(q.options, key=lambda o: o.position)
            questions.append(
                {
                    "id": q.id,
                    "text": q.text,
                    "marks": q.marks,
                    "position": q.position,
                    "options": [
                        {
                            "id": o.id,
                            "text": o.text,
                            "position": o.position,
                        }
                        for o in opts
                    ],
                }
            )
    return ExamDetailOut(
        id=exam.id,
        title=exam.title,
        subject=exam.subject,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        negative_marking=exam.negative_marking,
        shuffle_questions=exam.shuffle_questions,
        created_at=exam.created_at,
        question_count=len(qs),
        questions=questions,
    )
