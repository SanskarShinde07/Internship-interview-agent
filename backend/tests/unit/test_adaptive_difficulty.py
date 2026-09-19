import pytest

from app.adaptive.difficulty import (
    MAX_DIFFICULTY,
    MIN_DIFFICULTY,
    AnswerBand,
    classify_score,
    next_difficulty,
    reason_for_band,
)
from app.db.models import DifficultyChangeReason


@pytest.mark.parametrize(
    ("score", "expected_band"),
    [
        (100, AnswerBand.STRONG),
        (75, AnswerBand.STRONG),
        (74, AnswerBand.AVERAGE),
        (45, AnswerBand.AVERAGE),
        (44, AnswerBand.WEAK),
        (0, AnswerBand.WEAK),
    ],
)
def test_classify_score(score: int, expected_band: AnswerBand) -> None:
    assert classify_score(score) == expected_band


def test_strong_answer_increases_difficulty() -> None:
    assert next_difficulty(3, AnswerBand.STRONG) == 4


def test_weak_answer_decreases_difficulty() -> None:
    assert next_difficulty(3, AnswerBand.WEAK) == 2


def test_average_answer_keeps_difficulty() -> None:
    assert next_difficulty(3, AnswerBand.AVERAGE) == 3


def test_difficulty_clamped_at_max() -> None:
    assert next_difficulty(MAX_DIFFICULTY, AnswerBand.STRONG) == MAX_DIFFICULTY


def test_difficulty_clamped_at_min() -> None:
    assert next_difficulty(MIN_DIFFICULTY, AnswerBand.WEAK) == MIN_DIFFICULTY


def test_reason_for_band_maps_to_db_enum() -> None:
    assert reason_for_band(AnswerBand.STRONG) == DifficultyChangeReason.STRONG_ANSWER
    assert reason_for_band(AnswerBand.WEAK) == DifficultyChangeReason.WEAK_ANSWER
    assert reason_for_band(AnswerBand.AVERAGE) == DifficultyChangeReason.AVERAGE_ANSWER
