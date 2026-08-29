"""SQLAlchemy models for Imtihan."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="student")  # teacher | student
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    exams: Mapped[list["Exam"]] = relationship(back_populates="teacher")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="student")


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(100), default="General")
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    negative_marking: Mapped[float] = mapped_column(Float, default=0.25)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    teacher: Mapped["User"] = relationship(back_populates="exams")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan"
    )
    codes: Mapped[list["ExamCode"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(back_populates="exam")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    marks: Mapped[float] = mapped_column(Float, default=1.0)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    exam: Mapped["Exam"] = relationship(back_populates="questions")
    options: Mapped[list["Option"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class Option(Base):
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    text: Mapped[str] = mapped_column(String(500))
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    question: Mapped["Question"] = relationship(back_populates="options")


class ExamCode(Base):
    """One-time (or reused) codes students enter to join an exam."""

    __tablename__ = "exam_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=100)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    exam: Mapped["Exam"] = relationship(back_populates="codes")

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        now = utcnow()
        # SQLite returns naive datetimes; normalize for comparison
        if self.expires_at.tzinfo is None:
            now = now.replace(tzinfo=None)
        return self.expires_at < now

    def can_use(self) -> bool:
        return (not self.is_expired) and self.used_count < self.max_uses

    @classmethod
    def default_expiry(cls) -> datetime:
        return utcnow() + timedelta(days=settings.exam_code_ttl_days)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    code_id: Mapped[int | None] = mapped_column(ForeignKey("exam_codes.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_score: Mapped[float] = mapped_column(Float, default=0.0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    auto_submitted: Mapped[bool] = mapped_column(Boolean, default=False)

    exam: Mapped["Exam"] = relationship(back_populates="submissions")
    student: Mapped["User"] = relationship(back_populates="submissions")
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    option_id: Mapped[int | None] = mapped_column(ForeignKey("options.id"), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    earned: Mapped[float] = mapped_column(Float, default=0.0)

    submission: Mapped["Submission"] = relationship(back_populates="answers")

    # convenience denormalization for analytics
    question_meta: Mapped[dict] = mapped_column(JSON, default=dict)
