"""Overall score and readiness level (docs/BLUEPRINT.md §12).

Round weights reflect an ML engineering internship's actual emphasis:
ML theory weighted highest, then project understanding, then Python/NLP,
then scenario reasoning and behavioral fit lowest. Introduction is
excluded entirely - it's a warm-up, not evaluative.
"""

from app.db.models import ReadinessLevel, SessionState

ROUND_WEIGHTS: dict[SessionState, float] = {
    SessionState.PYTHON: 0.15,
    SessionState.MACHINE_LEARNING: 0.30,
    SessionState.NLP: 0.15,
    SessionState.PROJECT_DISCUSSION: 0.20,
    SessionState.SCENARIO: 0.10,
    SessionState.HR: 0.10,
}


def compute_overall_score(round_scores: dict[SessionState, float]) -> int | None:
    """`round_scores` should only include rounds with at least one scored
    answer. Weights are renormalized over whichever rounds are present, so
    a session terminated early still yields a meaningful overall score.
    """
    applicable = {
        round_: score for round_, score in round_scores.items() if round_ in ROUND_WEIGHTS
    }
    if not applicable:
        return None

    weight_sum = sum(ROUND_WEIGHTS[round_] for round_ in applicable)
    weighted_total = sum(score * ROUND_WEIGHTS[round_] for round_, score in applicable.items())
    return round(weighted_total / weight_sum)


def compute_readiness_level(overall_score: int) -> ReadinessLevel:
    if overall_score >= 80:
        return ReadinessLevel.STRONG
    if overall_score >= 65:
        return ReadinessLevel.READY
    if overall_score >= 45:
        return ReadinessLevel.DEVELOPING
    return ReadinessLevel.NOT_READY
