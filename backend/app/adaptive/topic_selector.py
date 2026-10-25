"""Topic/subtopic coverage tracking (docs/BLUEPRINT.md §8, §11).

The subtopic checklist for a round is derived from the question bank
itself (ordered by easiest-first) rather than hardcoded, so it can never
drift out of sync with the seed data.
"""

import random
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adaptive.difficulty import WEAK_THRESHOLD
from app.db.models import (
    AnswerEvaluation,
    BankRound,
    CandidateAnswer,
    InterviewQuestion,
    QuestionBankItem,
    QuestionRound,
)

COVERAGE_SCORE_THRESHOLD = 60


def get_subtopic_checklist(
    db: Session, bank_round: BankRound, session_id: uuid.UUID | None = None
) -> list[str]:
    """Easiest-difficulty-band first, as before. Within a band, the order
    is shuffled when session_id is given - seeded from (session_id,
    bank_round), so it's stable across repeated calls for the same
    session/round but differs between interviews. Every session otherwise
    walked the exact same subtopic order (min difficulty, then name) from
    the same starting difficulty, so a candidate who started several
    interviews got the identical opening questions every time; callers
    that only need the *set* of subtopics (e.g. completion_rules'
    coverage check) can omit session_id and get the plain deterministic
    order, since it doesn't matter there.

    Bands group two adjacent difficulty values (1-2, 3-4, ...) rather
    than shuffling within each exact difficulty value: most rounds' seed
    data has only one subtopic at the single lowest difficulty (e.g.
    Python has exactly one difficulty-1 item), so a same-value tier still
    made the opening question of a round identical across every session -
    just one shuffle group later than before the fix. Pairing adjacent
    values gives each band enough candidates to actually vary.
    """
    rows = db.execute(
        select(QuestionBankItem.subtopic, func.min(QuestionBankItem.difficulty))
        .where(
            QuestionBankItem.round == bank_round,
            QuestionBankItem.is_active.is_(True),
            QuestionBankItem.subtopic.is_not(None),
        )
        .group_by(QuestionBankItem.subtopic)
        .order_by(func.min(QuestionBankItem.difficulty), QuestionBankItem.subtopic)
    ).all()
    if session_id is None:
        return [row[0] for row in rows]

    rng = random.Random(f"{session_id}:{bank_round.value}")
    bands: dict[int, list[str]] = {}
    band_order: list[int] = []
    for subtopic, difficulty in rows:
        band = (difficulty - 1) // 2
        if band not in bands:
            bands[band] = []
            band_order.append(band)
        bands[band].append(subtopic)

    checklist: list[str] = []
    for band in band_order:
        subtopics = bands[band]
        rng.shuffle(subtopics)
        checklist.extend(subtopics)
    return checklist


def get_covered_subtopics(
    db: Session,
    session_id: uuid.UUID,
    round_: QuestionRound,
    threshold: int = COVERAGE_SCORE_THRESHOLD,
) -> set[str]:
    rows = db.execute(
        select(QuestionBankItem.subtopic)
        .join(InterviewQuestion, InterviewQuestion.question_bank_item_id == QuestionBankItem.id)
        .join(CandidateAnswer, CandidateAnswer.interview_question_id == InterviewQuestion.id)
        .join(AnswerEvaluation, AnswerEvaluation.candidate_answer_id == CandidateAnswer.id)
        .where(
            InterviewQuestion.session_id == session_id,
            InterviewQuestion.round == round_,
            AnswerEvaluation.composite_score >= threshold,
        )
    ).all()
    return {row[0] for row in rows if row[0] is not None}


def get_asked_subtopics(db: Session, session_id: uuid.UUID, round_: QuestionRound) -> list[str]:
    rows = db.execute(
        select(QuestionBankItem.subtopic)
        .join(InterviewQuestion, InterviewQuestion.question_bank_item_id == QuestionBankItem.id)
        .where(InterviewQuestion.session_id == session_id, InterviewQuestion.round == round_)
    ).all()
    return [row[0] for row in rows if row[0] is not None]


def next_subtopic_to_ask(
    db: Session, session_id: uuid.UUID, round_: QuestionRound, bank_round: BankRound
) -> str | None:
    """The next subtopic to probe: the first not-yet-asked item on the
    checklist, or - once every subtopic has been asked at least once -
    None, signaling the caller to fall back to any remaining unasked item.
    """
    checklist = get_subtopic_checklist(db, bank_round, session_id)
    asked = set(get_asked_subtopics(db, session_id, round_))
    for subtopic in checklist:
        if subtopic not in asked:
            return subtopic
    return None


def should_revisit_subtopic(
    db: Session, session_id: uuid.UUID, round_: QuestionRound, subtopic: str
) -> bool:
    """A subtopic is eligible for one simpler revisit if it was asked
    exactly once so far and that answer scored weak (docs/BLUEPRINT.md §8).
    """
    rows = db.execute(
        select(AnswerEvaluation.composite_score)
        .join(CandidateAnswer, CandidateAnswer.id == AnswerEvaluation.candidate_answer_id)
        .join(InterviewQuestion, InterviewQuestion.id == CandidateAnswer.interview_question_id)
        .join(QuestionBankItem, QuestionBankItem.id == InterviewQuestion.question_bank_item_id)
        .where(
            InterviewQuestion.session_id == session_id,
            InterviewQuestion.round == round_,
            QuestionBankItem.subtopic == subtopic,
        )
    ).all()
    if len(rows) != 1:
        return False
    (score,) = rows[0]
    return score < WEAK_THRESHOLD
