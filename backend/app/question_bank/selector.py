"""Question Bank Service selection algorithm (docs/BLUEPRINT.md §11).

Filters to the current round's active, not-yet-asked items; prefers the
next uncovered subtopic on the round's checklist; picks the closest
difficulty match among the remaining candidates; falls back to any
unasked item in the round once every subtopic has been touched at least
once. Returns None when the round's bank is exhausted, which signals the
orchestrator to end the round.

Note: the Adaptive Engine's weak-subtopic revisit policy
(`adaptive.topic_selector.should_revisit_subtopic`) needs a second,
easier item at the same subtopic to select. The current seed bank has
exactly one item per subtopic, so revisiting has nothing to select yet -
this activates automatically once a seed file gains multiple difficulty
variants per subtopic.
"""

import random
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adaptive import topic_selector
from app.db.models import BankRound, InterviewQuestion, QuestionBankItem, QuestionRound


def _closest_difficulty(
    items: list[QuestionBankItem], target_difficulty: int, session_id: uuid.UUID
) -> QuestionBankItem:
    closest = min(abs(item.difficulty - target_difficulty) for item in items)
    tied = [item for item in items if abs(item.difficulty - target_difficulty) == closest]
    # A stable, session-seeded pick among ties rather than always the
    # lowest item.id - otherwise this fallback path (reached once every
    # subtopic in the round has been asked at least once) reintroduces
    # the exact same "identical every attempt" bug the checklist shuffle
    # above fixes, just later in the round.
    rng = random.Random(f"{session_id}:{sorted(item.id for item in tied)}")
    return rng.choice(tied)


def select_next_bank_question(
    db: Session,
    session_id: uuid.UUID,
    round_: QuestionRound,
    bank_round: BankRound,
    target_difficulty: int,
) -> QuestionBankItem | None:
    asked_ids = select(InterviewQuestion.question_bank_item_id).where(
        InterviewQuestion.session_id == session_id,
        InterviewQuestion.question_bank_item_id.is_not(None),
    )
    base_query = select(QuestionBankItem).where(
        QuestionBankItem.round == bank_round,
        QuestionBankItem.is_active.is_(True),
        QuestionBankItem.id.not_in(asked_ids),
    )

    next_subtopic = topic_selector.next_subtopic_to_ask(db, session_id, round_, bank_round)
    if next_subtopic is not None:
        candidates = (
            db.execute(base_query.where(QuestionBankItem.subtopic == next_subtopic))
            .scalars()
            .all()
        )
        if candidates:
            return _closest_difficulty(candidates, target_difficulty, session_id)

    remaining = db.execute(base_query).scalars().all()
    if remaining:
        return _closest_difficulty(remaining, target_difficulty, session_id)

    return None
