"""Follow-up eligibility gate (docs/BLUEPRINT.md §8).

This is the deterministic gate; the LLM only writes the follow-up's
phrasing once the gate says yes. Project discussion is always eligible
(bounded by the per-topic cap); other rounds require a strong-enough
answer that surfaced a concept not yet probed.
"""

import re
from dataclasses import dataclass

from app.db.models import QuestionRound

FOLLOW_UP_SCORE_THRESHOLD = 60
DUPLICATE_SIMILARITY_THRESHOLD = 0.8


@dataclass(frozen=True)
class FollowUpDecision:
    eligible: bool
    concept: str | None = None


def is_followup_eligible(
    *,
    round_: QuestionRound,
    composite_score: int,
    mentioned_concepts: list[str],
    followups_used_for_topic: int,
    max_followups_per_topic: int,
) -> FollowUpDecision:
    if max_followups_per_topic <= 0 or followups_used_for_topic >= max_followups_per_topic:
        return FollowUpDecision(eligible=False)

    if round_ == QuestionRound.PROJECT_DISCUSSION:
        return FollowUpDecision(eligible=True)

    if composite_score >= FOLLOW_UP_SCORE_THRESHOLD and mentioned_concepts:
        return FollowUpDecision(eligible=True, concept=mentioned_concepts[0])

    return FollowUpDecision(eligible=False)


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {word for word in words if len(word) > 2}


def is_near_duplicate_question(
    candidate_text: str,
    previous_texts: list[str],
    threshold: float = DUPLICATE_SIMILARITY_THRESHOLD,
) -> bool:
    candidate_tokens = _tokenize(candidate_text)
    if not candidate_tokens:
        return False

    for previous in previous_texts:
        previous_tokens = _tokenize(previous)
        if not previous_tokens:
            continue
        intersection = len(candidate_tokens & previous_tokens)
        union = len(candidate_tokens | previous_tokens)
        if union and intersection / union >= threshold:
            return True

    return False
