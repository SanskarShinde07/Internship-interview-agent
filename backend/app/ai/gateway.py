"""AI Gateway (docs/BLUEPRINT.md §2, §9): the single choke point through
which the Orchestrator reaches language generation and answer evaluation.

`AIGateway` is the interface the orchestrator depends on. `StubAIGateway`
is a deterministic, non-LLM implementation used for Phase 2 so the
interview state machine and adaptive logic can be built and tested before
any real Gemini integration (Phase 3) exists. A `GeminiAIGateway` will
implement the same interface later without the orchestrator changing.
"""

from abc import ABC, abstractmethod

from app.ai.schemas import EvaluationOutput, InterviewerMode, InterviewerOutput
from app.db.models import QuestionType

_QUESTION_TYPE_FOR_MODE = {
    InterviewerMode.INTRO: QuestionType.INTRO,
    InterviewerMode.DELIVER_BANK_QUESTION: QuestionType.BANK,
    InterviewerMode.FOLLOW_UP: QuestionType.FOLLOW_UP,
    InterviewerMode.PROJECT: QuestionType.PROJECT,
}


class AIGateway(ABC):
    @abstractmethod
    def phrase_question(
        self,
        *,
        mode: InterviewerMode,
        bank_question_text: str | None = None,
        directive: str | None = None,
    ) -> InterviewerOutput: ...

    @abstractmethod
    def evaluate_answer(
        self,
        *,
        question_text: str,
        expected_concepts: list[str],
        transcript_text: str,
    ) -> EvaluationOutput: ...


class StubAIGateway(AIGateway):
    """Deterministic gateway with no LLM calls.

    Phrasing is templated instead of natural-language-generated.
    Evaluation scores an answer by keyword overlap between the transcript
    and the question's expected_concepts, which lets tests script
    strong/average/weak answers deterministically by choosing what
    concepts a fake transcript mentions.
    """

    _MIN_SUBSTANTIVE_LENGTH = 10

    def phrase_question(
        self,
        *,
        mode: InterviewerMode,
        bank_question_text: str | None = None,
        directive: str | None = None,
    ) -> InterviewerOutput:
        question_type = _QUESTION_TYPE_FOR_MODE.get(mode, QuestionType.FOLLOW_UP)

        if mode == InterviewerMode.DELIVER_BANK_QUESTION:
            text = bank_question_text or ""
        elif mode == InterviewerMode.INTRO:
            text = {
                "turn_1": "To start, tell me a bit about yourself and your background.",
                "turn_2": "What draws you specifically to machine learning engineering?",
            }.get(directive or "turn_1", "Tell me about yourself.")
        elif mode == InterviewerMode.FOLLOW_UP:
            concept = (directive or "that").replace("_", " ")
            text = f"Interesting - can you tell me more about {concept}?"
        elif mode == InterviewerMode.PROJECT:
            ordinal = "a" if directive == "project_1" else "another"
            text = f"Tell me about {ordinal} project you've worked on."
        else:
            text = directive or ""

        return InterviewerOutput(spoken_text=text, question_type=question_type)

    def evaluate_answer(
        self,
        *,
        question_text: str,
        expected_concepts: list[str],
        transcript_text: str,
    ) -> EvaluationOutput:
        transcript_lower = transcript_text.lower()
        mentioned = [
            concept
            for concept in expected_concepts
            if concept.replace("_", " ") in transcript_lower or concept in transcript_lower
        ]
        coverage_fraction = len(mentioned) / len(expected_concepts) if expected_concepts else 0.5
        score = round(coverage_fraction * 100)

        if len(transcript_text.strip()) < self._MIN_SUBSTANTIVE_LENGTH:
            score = min(score, 20)

        return EvaluationOutput(
            technical_accuracy=score,
            relevance=score,
            completeness=score,
            communication_clarity=score,
            concept_coverage=score,
            mentioned_concepts=mentioned,
            reasoning="stub evaluation based on keyword overlap with expected concepts",
        )
