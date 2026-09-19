"""Per-round configuration (docs/BLUEPRINT.md §7, §19 Phase 2).

This is orchestration-level knowledge (which rounds exist, in what order,
with what question-count and follow-up bounds) - distinct from the
Adaptive Engine's completion-rule *logic*, which takes these numbers as
plain parameters and knows nothing about round sequencing.
"""

from dataclasses import dataclass

from app.db.models import SessionState

ROUND_ORDER: list[SessionState] = [
    SessionState.INTRODUCTION,
    SessionState.PYTHON,
    SessionState.MACHINE_LEARNING,
    SessionState.NLP,
    SessionState.PROJECT_DISCUSSION,
    SessionState.SCENARIO,
    SessionState.HR,
]


@dataclass(frozen=True)
class RoundConfig:
    min_questions: int
    max_questions: int
    max_followups_per_topic: int
    scored: bool
    uses_bank: bool


ROUND_CONFIGS: dict[SessionState, RoundConfig] = {
    SessionState.INTRODUCTION: RoundConfig(
        min_questions=1, max_questions=2, max_followups_per_topic=0, scored=False, uses_bank=False
    ),
    SessionState.PYTHON: RoundConfig(
        min_questions=4, max_questions=6, max_followups_per_topic=2, scored=True, uses_bank=True
    ),
    SessionState.MACHINE_LEARNING: RoundConfig(
        min_questions=5, max_questions=8, max_followups_per_topic=2, scored=True, uses_bank=True
    ),
    SessionState.NLP: RoundConfig(
        min_questions=4, max_questions=6, max_followups_per_topic=2, scored=True, uses_bank=True
    ),
    SessionState.PROJECT_DISCUSSION: RoundConfig(
        min_questions=2,
        max_questions=6,
        max_followups_per_topic=3,
        scored=True,
        uses_bank=False,
    ),
    SessionState.SCENARIO: RoundConfig(
        min_questions=2, max_questions=4, max_followups_per_topic=1, scored=True, uses_bank=True
    ),
    SessionState.HR: RoundConfig(
        min_questions=2, max_questions=3, max_followups_per_topic=0, scored=True, uses_bank=True
    ),
}

MAX_TOP_LEVEL_PROJECTS = 2


def get_round_config(state: SessionState) -> RoundConfig:
    return ROUND_CONFIGS[state]


def expected_total_questions() -> int:
    """A rough baseline for progress/completion-rate estimates: the sum of
    every round's minimum question count. Not a hard prediction - actual
    interviews vary with follow-ups and adaptive branching.
    """
    return sum(config.min_questions for config in ROUND_CONFIGS.values())
