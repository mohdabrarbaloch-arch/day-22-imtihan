"""Pydantic v2 schemas — request/response contracts with validation."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


# ---------- Auth ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="student", pattern="^(teacher|student)$")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ---------- Users ----------
class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Exam ----------
class OptionIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    is_correct: bool = False


class QuestionIn(BaseModel):
    text: str = Field(min_length=1)
    marks: float = Field(default=1.0, gt=0, le=100)
    options: list[OptionIn] = Field(min_length=2, max_length=6)

    @model_validator(mode="after")
    def must_have_correct(self) -> "QuestionIn":
        if not any(o.is_correct for o in self.options):
            raise ValueError("Each question needs at least one correct option")
        return self


class ExamCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    subject: str = Field(default="General", max_length=100)
    description: str = Field(default="", max_length=2000)
    duration_minutes: int = Field(default=30, ge=1, le=300)
    negative_marking: float = Field(default=0.25, ge=0, le=1)
    shuffle_questions: bool = False
    questions: list[QuestionIn] = Field(min_length=1, max_length=200)


class ExamOut(BaseModel):
    id: int
    title: str
    subject: str
    description: str
    duration_minutes: int
    negative_marking: float
    shuffle_questions: bool
    created_at: datetime
    question_count: int = 0

    model_config = {"from_attributes": True}


class ExamDetailOut(ExamOut):
    questions: list["QuestionOut"] = []


class QuestionOut(BaseModel):
    id: int
    text: str
    marks: float
    position: int
    options: list["OptionOut"] = []

    model_config = {"from_attributes": True}


class OptionOut(BaseModel):
    id: int
    text: str
    position: int

    model_config = {"from_attributes": True}


# ---------- Exam codes ----------
class ExamCodeCreate(BaseModel):
    max_uses: int = Field(default=100, ge=1, le=10000)
    ttl_days: int | None = Field(default=None, ge=1, le=365)


class ExamCodeOut(BaseModel):
    id: int
    exam_id: int
    code: str
    max_uses: int
    used_count: int
    created_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}

class ExamJoinIn(BaseModel):
    code: str = Field(min_length=6, max_length=12)


# ---------- Submissions ----------
class AnswerIn(BaseModel):
    question_id: int
    option_id: int | None = None


class SubmitIn(BaseModel):
    code: str = Field(min_length=6, max_length=12)
    answers: list[AnswerIn] = Field(default_factory=list, max_length=300)


class AnswerOut(BaseModel):
    question_id: int
    option_id: int | None
    is_correct: bool
    earned: float


class SubmissionResult(BaseModel):
    submission_id: int
    exam_id: int
    exam_title: str
    score: float
    max_score: float
    correct_count: int
    wrong_count: int
    skipped_count: int
    percentage: float
    passed: bool
    pass_percentage: float = 40.0
    submitted_at: datetime
    auto_submitted: bool
    answers: list[AnswerOut] = []


class SubmissionOut(BaseModel):
    id: int
    exam_id: int
    exam_title: str = ""
    student_name: str = ""
    score: float | None
    max_score: float
    percentage: float | None
    submitted_at: datetime | None
    auto_submitted: bool

    model_config = {"from_attributes": True}


# ---------- Analytics ----------
class QuestionStat(BaseModel):
    question_id: int
    text: str
    marks: float
    attempts: int
    correct: int
    wrong: int
    skipped: int
    accuracy: float  # 0-100


class ExamAnalytics(BaseModel):
    exam_id: int
    exam_title: str
    total_submissions: int
    average_score: float
    highest_score: float
    lowest_score: float
    pass_rate: float  # 0-100
    pass_percentage: float
    question_stats: list[QuestionStat]


# Forward refs
ExamDetailOut.model_rebuild()
