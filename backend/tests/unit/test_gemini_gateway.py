"""Tests the real Gemini gateway against a mocked SDK - no live API calls,
per docs/BLUEPRINT.md §18 ("AI output validation tests... run against
fixtures, not live Gemini calls, to keep CI fast/free").
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.ai.gateway import GeminiAIGateway
from app.ai.schemas import InterviewerMode
from app.db.models import QuestionType


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


@pytest.fixture
def gateway() -> GeminiAIGateway:
    with (
        patch("app.ai.gateway.genai.GenerativeModel", side_effect=lambda *a, **k: MagicMock()),
        patch("app.ai.gateway.genai.configure"),
    ):
        return GeminiAIGateway(
            api_key="fake-key",
            model_name="gemini-test",
            request_timeout_seconds=5.0,
            max_retries=1,
        )


def test_phrase_question_success(gateway: GeminiAIGateway) -> None:
    gateway._interviewer_model.generate_content.return_value = FakeResponse(
        "Tell me about yourself."
    )
    output = gateway.phrase_question(mode=InterviewerMode.INTRO, directive="turn_1")
    assert output.spoken_text == "Tell me about yourself."
    assert output.question_type == QuestionType.INTRO


def test_phrase_question_falls_back_to_verbatim_bank_text_after_repeated_failures(
    gateway: GeminiAIGateway,
) -> None:
    gateway._interviewer_model.generate_content.side_effect = RuntimeError("network error")
    output = gateway.phrase_question(
        mode=InterviewerMode.DELIVER_BANK_QUESTION,
        bank_question_text="What is overfitting?",
    )
    assert output.spoken_text == "What is overfitting?"
    assert output.question_type == QuestionType.BANK
    # max_retries=1 -> two attempts total before falling back
    assert gateway._interviewer_model.generate_content.call_count == 2


def test_phrase_question_falls_back_on_empty_response(gateway: GeminiAIGateway) -> None:
    gateway._interviewer_model.generate_content.return_value = FakeResponse("   ")
    output = gateway.phrase_question(
        mode=InterviewerMode.DELIVER_BANK_QUESTION,
        bank_question_text="What is a decision tree?",
    )
    assert output.spoken_text == "What is a decision tree?"


def test_evaluate_answer_success(gateway: GeminiAIGateway) -> None:
    payload = {
        "technical_accuracy": 80,
        "relevance": 85,
        "completeness": 75,
        "communication_clarity": 90,
        "concept_coverage": 70,
        "mentioned_concepts": ["overfitting"],
        "reasoning": "Solid, well-structured answer.",
    }
    gateway._evaluator_model.generate_content.return_value = FakeResponse(json.dumps(payload))
    result = gateway.evaluate_answer(
        question_text="What is overfitting?",
        expected_concepts=["overfitting", "generalization"],
        transcript_text="Overfitting is when a model memorizes training data.",
    )
    assert result.technical_accuracy == 80
    assert result.mentioned_concepts == ["overfitting"]
    assert result.fallback is False


def test_evaluate_answer_falls_back_on_malformed_json(gateway: GeminiAIGateway) -> None:
    gateway._evaluator_model.generate_content.return_value = FakeResponse("not json at all")
    result = gateway.evaluate_answer(
        question_text="q", expected_concepts=[], transcript_text="answer"
    )
    assert result.fallback is True
    assert result.technical_accuracy == 50


def test_evaluate_answer_falls_back_on_out_of_range_score(gateway: GeminiAIGateway) -> None:
    payload = {
        "technical_accuracy": 900,
        "relevance": 80,
        "completeness": 80,
        "communication_clarity": 80,
        "concept_coverage": 80,
        "mentioned_concepts": [],
        "reasoning": "x",
    }
    gateway._evaluator_model.generate_content.return_value = FakeResponse(json.dumps(payload))
    result = gateway.evaluate_answer(
        question_text="q", expected_concepts=[], transcript_text="answer"
    )
    assert result.fallback is True


def test_evaluate_answer_falls_back_on_repeated_exception(gateway: GeminiAIGateway) -> None:
    gateway._evaluator_model.generate_content.side_effect = RuntimeError("timeout")
    result = gateway.evaluate_answer(
        question_text="q", expected_concepts=[], transcript_text="answer"
    )
    assert result.fallback is True
    assert gateway._evaluator_model.generate_content.call_count == 2
