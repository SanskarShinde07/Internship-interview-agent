"""Structured contracts for AI agent calls (docs/BLUEPRINT.md §9).

These are the typed boundary between the deterministic backend and
whatever generates language (a stub in Phase 2, real Gemini calls in
Phase 3). The orchestrator only ever reads these fields - never raw
model output - which is what keeps LLM behavior from leaking into
interview control flow.
"""

import enum

from pydantic import BaseModel, Field

from app.db.models import QuestionType


class InterviewerMode(str, enum.Enum):
    INTRO = "INTRO"
    DELIVER_BANK_QUESTION = "DELIVER_BANK_QUESTION"
    FOLLOW_UP = "FOLLOW_UP"
    PROJECT = "PROJECT"
    TRANSITION = "TRANSITION"
    CLOSING = "CLOSING"


class InterviewerOutput(BaseModel):
    spoken_text: str
    question_type: QuestionType


class EvaluationOutput(BaseModel):
    technical_accuracy: int = Field(ge=0, le=100)
    relevance: int = Field(ge=0, le=100)
    completeness: int = Field(ge=0, le=100)
    communication_clarity: int = Field(ge=0, le=100)
    concept_coverage: int = Field(ge=0, le=100)
    mentioned_concepts: list[str] = Field(default_factory=list)
    reasoning: str = ""
    fallback: bool = False
