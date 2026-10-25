"""Request/response DTOs for the API layer (docs/BLUEPRINT.md §6).

Kept separate from app.db.models: these are the wire contract, not the
storage schema, and the two are free to diverge as either evolves.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.db.models import SessionState


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str | None = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None


class AuthResponse(BaseModel):
    access_token: str
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)


class ResetPasswordResponse(BaseModel):
    message: str


class SessionHistoryItem(BaseModel):
    session_id: uuid.UUID
    state: SessionState
    started_at: datetime | None
    completed_at: datetime | None
    overall_score: int | None
    readiness_level: str | None


class SessionHistoryResponse(BaseModel):
    sessions: list[SessionHistoryItem]


class CreateSessionRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)


class SessionSummaryResponse(BaseModel):
    session_id: uuid.UUID
    state: SessionState


class QuestionResponse(BaseModel):
    question_id: uuid.UUID
    question_text: str
    round: str
    difficulty: int


class StartSessionResponse(BaseModel):
    state: SessionState
    current_question: QuestionResponse


class SessionProgressResponse(BaseModel):
    state: SessionState
    round: str
    difficulty: int
    progress: dict[str, int]


class SubmitAnswerRequest(BaseModel):
    question_id: uuid.UUID
    transcript_text: str = Field(min_length=1, max_length=4000)
    duration_seconds: float | None = Field(default=None, ge=0)


class NextStepResponse(BaseModel):
    state: SessionState
    next_question: QuestionResponse | None = None


class RepeatQuestionResponse(BaseModel):
    question_text: str


class EndSessionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class EndSessionResponse(BaseModel):
    state: SessionState


class ReportResponse(BaseModel):
    overall_score: int
    category_scores: dict[str, float | None]
    strengths: list[str]
    improvements: list[str]
    recruiter_summary: str
    learning_roadmap: list[dict[str, Any]]
    readiness_level: str


class AnalyticsResponse(BaseModel):
    interview_duration_seconds: float | None
    total_questions: int
    questions_per_round: dict[str, int]
    follow_up_questions: int
    difficulty_progression: list[dict[str, Any]]
    highest_difficulty_reached: int | None
    topic_wise_scores: dict[str, float]
    average_technical_score: float | None
    average_communication_score: float | None
    average_answer_length: float | None
    strongest_topic: str | None
    weakest_topic: str | None
    round_completion_times_seconds: dict[str, float]
    interview_completion_rate: float
    adaptive_difficulty_changes: int
    interview_timeline: list[dict[str, Any]]


class CoachMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    referenced_question_id: uuid.UUID | None = None


class CoachMessageResponse(BaseModel):
    reply: str
    conversation_id: uuid.UUID


class CoachMessageItem(BaseModel):
    role: str
    content: str
    referenced_question_id: uuid.UUID | None = None


class CoachMessagesListResponse(BaseModel):
    messages: list[CoachMessageItem]


class ErrorResponse(BaseModel):
    error_code: str
    message: str
