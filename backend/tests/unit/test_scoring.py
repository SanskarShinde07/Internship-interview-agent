from app.ai.schemas import EvaluationOutput
from app.db.models import ReadinessLevel, SessionState
from app.scoring.overall_score import compute_overall_score, compute_readiness_level
from app.scoring.question_score import compute_composite_score
from app.scoring.round_score import compute_average_score


def test_compute_composite_score_all_max() -> None:
    evaluation = EvaluationOutput(
        technical_accuracy=100,
        relevance=100,
        completeness=100,
        communication_clarity=100,
        concept_coverage=100,
    )
    assert compute_composite_score(evaluation) == 100


def test_compute_composite_score_weights_technical_accuracy_most() -> None:
    high_technical = EvaluationOutput(
        technical_accuracy=100,
        relevance=0,
        completeness=0,
        communication_clarity=0,
        concept_coverage=0,
    )
    high_communication = EvaluationOutput(
        technical_accuracy=0,
        relevance=0,
        completeness=0,
        communication_clarity=100,
        concept_coverage=0,
    )
    assert compute_composite_score(high_technical) > compute_composite_score(high_communication)


def test_compute_average_score_empty() -> None:
    assert compute_average_score([]) is None


def test_compute_average_score() -> None:
    assert compute_average_score([80, 60, 100]) == 80.0


def test_compute_overall_score_renormalizes_over_present_rounds() -> None:
    # Only ML and HR answered (e.g. session terminated early) - weights
    # should renormalize rather than silently averaging in zeros.
    score = compute_overall_score(
        {SessionState.MACHINE_LEARNING: 90.0, SessionState.HR: 90.0}
    )
    assert score == 90


def test_compute_overall_score_no_rounds() -> None:
    assert compute_overall_score({}) is None


def test_readiness_level_thresholds() -> None:
    assert compute_readiness_level(85) == ReadinessLevel.STRONG
    assert compute_readiness_level(70) == ReadinessLevel.READY
    assert compute_readiness_level(50) == ReadinessLevel.DEVELOPING
    assert compute_readiness_level(20) == ReadinessLevel.NOT_READY
