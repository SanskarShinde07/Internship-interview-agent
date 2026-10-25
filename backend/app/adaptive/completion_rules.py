"""Round- and session-level completion rules (docs/BLUEPRINT.md §7, §8).

Takes plain parameters rather than an orchestrator config object so this
module has no dependency on the orchestrator - the orchestrator depends
on the Adaptive Engine, never the other way around.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adaptive import topic_selector
from app.db.models import BankRound, InterviewQuestion, QuestionRound


def count_questions_in_round(db: Session, session_id: uuid.UUID, round_: QuestionRound) -> int:
    return db.execute(
        select(func.count())
        .select_from(InterviewQuestion)
        .where(InterviewQuestion.session_id == session_id, InterviewQuestion.round == round_)
    ).scalar_one()


def is_round_complete(
    db: Session,
    session_id: uuid.UUID,
    round_: QuestionRound,
    *,
    min_questions: int,
    max_questions: int,
    uses_bank: bool,
) -> bool:
    asked = count_questions_in_round(db, session_id, round_)
    if asked >= max_questions:
        return True
    if asked < min_questions:
        return False
    if uses_bank:
        bank_round = BankRound(round_.value)
        checklist = topic_selector.get_subtopic_checklist(db, bank_round)
        covered = topic_selector.get_covered_subtopics(db, session_id, round_)
        return set(checklist).issubset(covered)
    # Non-bank rounds (INTRODUCTION, PROJECT_DISCUSSION): reaching the
    # minimum isn't itself completion - the caller's generation logic
    # decides when there's nothing more to ask.
    return False


def session_should_terminate_for_limits(
    *,
    total_questions_in_session: int,
    started_at: datetime | None,
    max_questions_per_session: int,
    max_session_duration_minutes: int,
) -> tuple[bool, str | None]:
    if total_questions_in_session >= max_questions_per_session:
        return True, "max_questions_reached"
    if started_at is not None:
        # SQLite doesn't round-trip tzinfo, so a reloaded ORM instance can
        # come back naive even though it was always written in UTC.
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        elapsed = datetime.now(UTC) - started_at
        if elapsed >= timedelta(minutes=max_session_duration_minutes):
            return True, "max_duration_reached"
    return False, None
