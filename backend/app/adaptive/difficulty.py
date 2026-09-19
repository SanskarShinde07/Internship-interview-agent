"""Difficulty adjustment (docs/BLUEPRINT.md §8). Pure deterministic logic -
the LLM never decides this; it only supplies the composite score that
feeds in.
"""

import enum

from app.db.models import DifficultyChangeReason

STRONG_THRESHOLD = 75
WEAK_THRESHOLD = 45

MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 5


class AnswerBand(str, enum.Enum):
    STRONG = "STRONG"
    AVERAGE = "AVERAGE"
    WEAK = "WEAK"


def classify_score(composite_score: int) -> AnswerBand:
    if composite_score >= STRONG_THRESHOLD:
        return AnswerBand.STRONG
    if composite_score < WEAK_THRESHOLD:
        return AnswerBand.WEAK
    return AnswerBand.AVERAGE


def next_difficulty(current_difficulty: int, band: AnswerBand) -> int:
    if band == AnswerBand.STRONG:
        return min(MAX_DIFFICULTY, current_difficulty + 1)
    if band == AnswerBand.WEAK:
        return max(MIN_DIFFICULTY, current_difficulty - 1)
    return current_difficulty


_REASON_FOR_BAND = {
    AnswerBand.STRONG: DifficultyChangeReason.STRONG_ANSWER,
    AnswerBand.AVERAGE: DifficultyChangeReason.AVERAGE_ANSWER,
    AnswerBand.WEAK: DifficultyChangeReason.WEAK_ANSWER,
}


def reason_for_band(band: AnswerBand) -> DifficultyChangeReason:
    return _REASON_FOR_BAND[band]
