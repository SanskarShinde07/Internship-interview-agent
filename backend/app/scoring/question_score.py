"""Per-answer composite score (docs/BLUEPRINT.md §12).

Weighted average of the Evaluator Agent's five dimensions. The Evaluator
Agent only ever supplies the five raw sub-scores; this math is what turns
them into the one number the Adaptive Engine and reports actually use.
"""

from app.ai.schemas import EvaluationOutput

WEIGHTS = {
    "technical_accuracy": 0.40,
    "completeness": 0.20,
    "relevance": 0.15,
    "communication_clarity": 0.15,
    "concept_coverage": 0.10,
}


def compute_composite_score(evaluation: EvaluationOutput) -> int:
    total = sum(getattr(evaluation, dimension) * weight for dimension, weight in WEIGHTS.items())
    return round(total)
