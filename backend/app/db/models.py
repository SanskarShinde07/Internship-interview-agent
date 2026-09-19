import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Naming convention keeps Alembic autogenerate diffs stable across SQLite/Postgres.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _utcnow() -> datetime:
    return datetime.now(UTC)


# --- Enums (docs/BLUEPRINT.md §5, §7, §11, §12) --------------------------------


class SessionState(str, enum.Enum):
    CREATED = "CREATED"
    INTRODUCTION = "INTRODUCTION"
    PYTHON = "PYTHON"
    MACHINE_LEARNING = "MACHINE_LEARNING"
    NLP = "NLP"
    PROJECT_DISCUSSION = "PROJECT_DISCUSSION"
    SCENARIO = "SCENARIO"
    HR = "HR"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"


# Rounds that have a static, curated question bank (docs/BLUEPRINT.md §11).
# INTRODUCTION and PROJECT_DISCUSSION are always dynamically generated.
class BankRound(str, enum.Enum):
    PYTHON = "PYTHON"
    MACHINE_LEARNING = "MACHINE_LEARNING"
    NLP = "NLP"
    SCENARIO = "SCENARIO"
    HR = "HR"


# Rounds an asked question can belong to (superset of BankRound).
class QuestionRound(str, enum.Enum):
    INTRODUCTION = "INTRODUCTION"
    PYTHON = "PYTHON"
    MACHINE_LEARNING = "MACHINE_LEARNING"
    NLP = "NLP"
    PROJECT_DISCUSSION = "PROJECT_DISCUSSION"
    SCENARIO = "SCENARIO"
    HR = "HR"


class QuestionType(str, enum.Enum):
    BANK = "BANK"
    FOLLOW_UP = "FOLLOW_UP"
    PROJECT = "PROJECT"
    SCENARIO = "SCENARIO"
    BEHAVIORAL = "BEHAVIORAL"
    INTRO = "INTRO"


class DifficultyChangeReason(str, enum.Enum):
    STRONG_ANSWER = "STRONG_ANSWER"
    WEAK_ANSWER = "WEAK_ANSWER"
    AVERAGE_ANSWER = "AVERAGE_ANSWER"


class ReadinessLevel(str, enum.Enum):
    NOT_READY = "NOT_READY"
    DEVELOPING = "DEVELOPING"
    READY = "READY"
    STRONG = "STRONG"


class MessageRole(str, enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


# --- Tables ---------------------------------------------------------------------


class User(Base):
    """A registered account (docs/BLUEPRINT.md §21 follow-up: optional auth
    so a candidate can see their own interview history across sessions).
    Entirely separate from Candidate: a session can still be fully
    anonymous, or its Candidate row can be linked to a User when the
    candidate was signed in at the time they started it.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    candidates: Mapped[list["Candidate"]] = relationship(back_populates="user")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User | None] = relationship(back_populates="candidates")
    sessions: Mapped[list["InterviewSession"]] = relationship(back_populates="candidate")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("candidates.id"), nullable=True
    )
    target_role: Mapped[str] = mapped_column(String(100), default="ml_engineer_intern")
    state: Mapped[SessionState] = mapped_column(
        Enum(SessionState, native_enum=False), default=SessionState.CREATED
    )
    current_difficulty: Mapped[int] = mapped_column(Integer, default=2)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    termination_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

    candidate: Mapped[Candidate | None] = relationship(back_populates="sessions")
    questions: Mapped[list["InterviewQuestion"]] = relationship(back_populates="session")
    difficulty_log: Mapped[list["DifficultyLog"]] = relationship(back_populates="session")
    report: Mapped["InterviewReport | None"] = relationship(back_populates="session")
    coach_conversations: Mapped[list["CoachConversation"]] = relationship(
        back_populates="session"
    )


class QuestionBankItem(Base):
    __tablename__ = "question_bank_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    round: Mapped[BankRound] = mapped_column(Enum(BankRound, native_enum=False))
    topic: Mapped[str] = mapped_column(String(100))
    subtopic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer)
    question_text: Mapped[str] = mapped_column(Text)
    expected_concepts: Mapped[list] = mapped_column(JSON, default=list)
    followup_hints: Mapped[list | None] = mapped_column(JSON, nullable=True)
    prerequisites: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    asked_instances: Mapped[list["InterviewQuestion"]] = relationship(
        back_populates="question_bank_item"
    )


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_sessions.id"))
    question_bank_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("question_bank_items.id"), nullable=True
    )
    parent_question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("interview_questions.id"), nullable=True
    )
    round: Mapped[QuestionRound] = mapped_column(Enum(QuestionRound, native_enum=False))
    topic: Mapped[str] = mapped_column(String(100))
    difficulty: Mapped[int] = mapped_column(Integer)
    sequence_number: Mapped[int] = mapped_column(Integer)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType, native_enum=False))
    question_text: Mapped[str] = mapped_column(Text)
    asked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped[InterviewSession] = relationship(back_populates="questions")
    question_bank_item: Mapped[QuestionBankItem | None] = relationship(
        back_populates="asked_instances"
    )
    parent_question: Mapped["InterviewQuestion | None"] = relationship(
        remote_side=[id], back_populates="follow_ups"
    )
    follow_ups: Mapped[list["InterviewQuestion"]] = relationship(back_populates="parent_question")
    answer: Mapped["CandidateAnswer | None"] = relationship(back_populates="question")


class CandidateAnswer(Base):
    __tablename__ = "candidate_answers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    interview_question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_questions.id"), unique=True
    )
    transcript_text: Mapped[str] = mapped_column(Text)
    answer_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    question: Mapped[InterviewQuestion] = relationship(back_populates="answer")
    evaluation: Mapped["AnswerEvaluation | None"] = relationship(back_populates="answer")


class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    candidate_answer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_answers.id"), unique=True
    )
    technical_accuracy: Mapped[int] = mapped_column(Integer)
    relevance: Mapped[int] = mapped_column(Integer)
    completeness: Mapped[int] = mapped_column(Integer)
    communication_clarity: Mapped[int] = mapped_column(Integer)
    concept_coverage: Mapped[int] = mapped_column(Integer)
    composite_score: Mapped[int] = mapped_column(Integer)
    evaluator_reasoning: Mapped[str] = mapped_column(Text)
    flags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    answer: Mapped[CandidateAnswer] = relationship(back_populates="evaluation")


class DifficultyLog(Base):
    __tablename__ = "difficulty_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_sessions.id"))
    sequence_number: Mapped[int] = mapped_column(Integer)
    previous_difficulty: Mapped[int] = mapped_column(Integer)
    new_difficulty: Mapped[int] = mapped_column(Integer)
    reason: Mapped[DifficultyChangeReason] = mapped_column(
        Enum(DifficultyChangeReason, native_enum=False)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped[InterviewSession] = relationship(back_populates="difficulty_log")


class InterviewReport(Base):
    __tablename__ = "interview_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id"), unique=True
    )
    overall_score: Mapped[int] = mapped_column(Integer)
    category_scores: Mapped[dict] = mapped_column(JSON)
    strengths: Mapped[list] = mapped_column(JSON)
    improvements: Mapped[list] = mapped_column(JSON)
    recruiter_summary: Mapped[str] = mapped_column(Text)
    learning_roadmap: Mapped[list] = mapped_column(JSON)
    readiness_level: Mapped[ReadinessLevel] = mapped_column(Enum(ReadinessLevel, native_enum=False))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped[InterviewSession] = relationship(back_populates="report")


class CoachConversation(Base):
    __tablename__ = "coach_conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_sessions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped[InterviewSession] = relationship(back_populates="coach_conversations")
    messages: Mapped[list["CoachMessage"]] = relationship(back_populates="conversation")


class CoachMessage(Base):
    __tablename__ = "coach_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coach_conversations.id"))
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, native_enum=False))
    content: Mapped[str] = mapped_column(Text)
    referenced_question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("interview_questions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation: Mapped[CoachConversation] = relationship(back_populates="messages")
