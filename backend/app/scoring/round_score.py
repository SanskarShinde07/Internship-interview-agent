"""Round and topic scores (docs/BLUEPRINT.md §12): a plain average of the
composite scores of the answers that make up the group. No difficulty
weighting - a candidate who earned a higher difficulty already has higher
underlying scores, so weighting difficulty too would double-count it.
"""


def compute_average_score(composite_scores: list[int]) -> float | None:
    if not composite_scores:
        return None
    return sum(composite_scores) / len(composite_scores)
