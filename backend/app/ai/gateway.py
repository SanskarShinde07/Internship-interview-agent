"""AI Gateway (docs/BLUEPRINT.md §2, §9): the single choke point through
which the Orchestrator reaches language generation and answer evaluation.

`AIGateway` is the interface the orchestrator depends on.

`StubAIGateway` is a deterministic, non-LLM implementation used in tests
and as the safety-net fallback when Gemini is unavailable - it's what
proved the interview state machine and adaptive logic correct in Phase 2
before any real model call existed.

`GeminiAIGateway` is the real implementation (Phase 3): it calls Gemini
for phrasing and evaluation, validates every response against the same
typed schemas, and falls back to deterministic behavior on failure so a
model outage or a malformed response never crashes an interview in
progress (docs/BLUEPRINT.md §16).
"""

import json
import logging
from abc import ABC, abstractmethod

import google.generativeai as genai
from pydantic import ValidationError

from app.ai.prompts import coach as coach_prompts
from app.ai.prompts import evaluator as evaluator_prompts
from app.ai.prompts import interviewer as interviewer_prompts
from app.ai.prompts import recruiter as recruiter_prompts
from app.ai.schemas import (
    CoachReplyOutput,
    EvaluationOutput,
    InterviewerMode,
    InterviewerOutput,
    LearningRoadmapItem,
    RecruiterNarrativeOutput,
)
from app.config import get_settings
from app.db.models import QuestionType

logger = logging.getLogger(__name__)

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

    @abstractmethod
    def generate_recruiter_narrative(
        self,
        *,
        overall_score: int,
        readiness_level: str,
        category_scores: dict[str, float | None],
        strong_topics: list[str],
        weak_topics: list[str],
    ) -> RecruiterNarrativeOutput: ...

    @abstractmethod
    def coach_reply(self, *, candidate_message: str, context_text: str) -> CoachReplyOutput: ...


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

    def generate_recruiter_narrative(
        self,
        *,
        overall_score: int,
        readiness_level: str,
        category_scores: dict[str, float | None],
        strong_topics: list[str],
        weak_topics: list[str],
    ) -> RecruiterNarrativeOutput:
        strengths = [
            f"Demonstrated solid understanding of {topic.replace('_', ' ')}."
            for topic in strong_topics
        ] or ["Completed the full interview with consistent, on-topic effort."]

        improvements = [
            f"Review the fundamentals of {topic.replace('_', ' ')} and practice related problems."
            for topic in weak_topics
        ] or ["Continue practicing to build further depth across topics."]

        strong_summary = ", ".join(t.replace("_", " ") for t in strong_topics[:3]) or "a few areas"
        weak_summary = ", ".join(t.replace("_", " ") for t in weak_topics[:3]) or "some areas"
        summary = (
            f"The candidate scored {overall_score}/100 overall ({readiness_level.title()}), "
            f"showing particular strength in {strong_summary} and room to grow in {weak_summary}."
        )

        roadmap = [
            LearningRoadmapItem(
                topic=topic,
                action=(
                    f"Study {topic.replace('_', ' ')} fundamentals and "
                    "solve practice problems on it."
                ),
                priority="HIGH",
            )
            for topic in weak_topics
        ]

        return RecruiterNarrativeOutput(
            recruiter_summary=summary,
            strengths=strengths,
            improvements=improvements,
            learning_roadmap=roadmap,
        )

    def coach_reply(self, *, candidate_message: str, context_text: str) -> CoachReplyOutput:
        return CoachReplyOutput(
            reply=(
                "Here is what your interview record shows for this: "
                f"{context_text[:400]}"
            )
        )


class GeminiAIGateway(AIGateway):
    """Real Gemini-backed implementation of the AI Gateway.

    Every response is validated before it ever reaches the orchestrator:
    `evaluate_answer` parses and validates JSON against `EvaluationOutput`
    (out-of-range or missing fields raise, triggering the fallback path).
    A failure - network error, timeout, or a response that doesn't parse -
    is retried once, then falls back to deterministic behavior rather than
    raising into the interview flow.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        request_timeout_seconds: float,
        max_retries: int,
    ) -> None:
        genai.configure(api_key=api_key)
        self._request_options = {"timeout": request_timeout_seconds}
        self._max_retries = max_retries
        self._interviewer_model = genai.GenerativeModel(
            model_name, system_instruction=interviewer_prompts.SYSTEM_PROMPT
        )
        self._evaluator_model = genai.GenerativeModel(
            model_name, system_instruction=evaluator_prompts.SYSTEM_PROMPT
        )
        self._recruiter_model = genai.GenerativeModel(
            model_name, system_instruction=recruiter_prompts.SYSTEM_PROMPT
        )
        self._coach_model = genai.GenerativeModel(
            model_name, system_instruction=coach_prompts.SYSTEM_PROMPT
        )
        self._fallback = StubAIGateway()

    def _generate(self, model: genai.GenerativeModel, prompt: str, **generation_kwargs) -> str:
        last_error: Exception | None = None
        for _attempt in range(self._max_retries + 1):
            try:
                response = model.generate_content(
                    prompt,
                    request_options=self._request_options,
                    **generation_kwargs,
                )
                return response.text
            except Exception as exc:  # noqa: BLE001 - any failure here must fall back, not crash
                last_error = exc
                logger.warning("Gemini call failed (will retry/fallback): %s", exc)
        raise last_error  # guaranteed set: the loop always runs >=1 iteration

    def phrase_question(
        self,
        *,
        mode: InterviewerMode,
        bank_question_text: str | None = None,
        directive: str | None = None,
    ) -> InterviewerOutput:
        question_type = _QUESTION_TYPE_FOR_MODE.get(mode, QuestionType.FOLLOW_UP)
        prompt = interviewer_prompts.build_user_prompt(
            mode=mode, bank_question_text=bank_question_text, directive=directive
        )
        try:
            text = self._generate(self._interviewer_model, prompt).strip()
            if not text:
                raise ValueError("empty response from Gemini")
            return InterviewerOutput(spoken_text=text, question_type=question_type)
        except Exception:
            logger.warning("Falling back to templated phrasing for mode=%s", mode)
            return self._fallback.phrase_question(
                mode=mode, bank_question_text=bank_question_text, directive=directive
            )

    def evaluate_answer(
        self,
        *,
        question_text: str,
        expected_concepts: list[str],
        transcript_text: str,
    ) -> EvaluationOutput:
        prompt = evaluator_prompts.build_user_prompt(
            question_text=question_text,
            expected_concepts=expected_concepts,
            transcript_text=transcript_text,
        )
        try:
            raw_text = self._generate(
                self._evaluator_model,
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json"),
            )
            parsed = json.loads(raw_text)
            return EvaluationOutput(**parsed)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            logger.warning("Gemini evaluation response failed validation: %s", exc)
        except Exception as exc:  # noqa: BLE001 - network/timeout/etc. after retries
            logger.warning("Gemini evaluation call failed: %s", exc)

        return EvaluationOutput(
            technical_accuracy=50,
            relevance=50,
            completeness=50,
            communication_clarity=50,
            concept_coverage=50,
            mentioned_concepts=[],
            reasoning="Evaluation unavailable; conservative default score applied.",
            fallback=True,
        )

    def generate_recruiter_narrative(
        self,
        *,
        overall_score: int,
        readiness_level: str,
        category_scores: dict[str, float | None],
        strong_topics: list[str],
        weak_topics: list[str],
    ) -> RecruiterNarrativeOutput:
        prompt = recruiter_prompts.build_user_prompt(
            overall_score=overall_score,
            readiness_level=readiness_level,
            category_scores=category_scores,
            strong_topics=strong_topics,
            weak_topics=weak_topics,
        )
        try:
            raw_text = self._generate(
                self._recruiter_model,
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json"),
            )
            parsed = json.loads(raw_text)
            return RecruiterNarrativeOutput(**parsed)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            logger.warning("Gemini recruiter narrative failed validation: %s", exc)
        except Exception as exc:  # noqa: BLE001 - network/timeout/etc. after retries
            logger.warning("Gemini recruiter narrative call failed: %s", exc)

        fallback_result = self._fallback.generate_recruiter_narrative(
            overall_score=overall_score,
            readiness_level=readiness_level,
            category_scores=category_scores,
            strong_topics=strong_topics,
            weak_topics=weak_topics,
        )
        fallback_result.fallback = True
        return fallback_result

    def coach_reply(self, *, candidate_message: str, context_text: str) -> CoachReplyOutput:
        prompt = coach_prompts.build_user_prompt(
            candidate_message=candidate_message, context_text=context_text
        )
        try:
            text = self._generate(self._coach_model, prompt).strip()
            if not text:
                raise ValueError("empty response from Gemini")
            return CoachReplyOutput(reply=text)
        except Exception as exc:  # noqa: BLE001 - any failure here must fall back, not crash
            logger.warning("Gemini coach reply failed, falling back: %s", exc)
            fallback_result = self._fallback.coach_reply(
                candidate_message=candidate_message, context_text=context_text
            )
            fallback_result.fallback = True
            return fallback_result


def get_default_gateway() -> AIGateway:
    """Returns the real Gemini gateway when an API key is configured,
    otherwise the deterministic stub - so local development and CI never
    need a live key to run.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        return StubAIGateway()

    return GeminiAIGateway(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
        request_timeout_seconds=settings.gemini_request_timeout_seconds,
        max_retries=settings.gemini_max_retries,
    )
