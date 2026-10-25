"""Regression coverage for a reported bug: a candidate who started
several interviews got the exact same opening questions every time.
Root cause was topic_selector.get_subtopic_checklist returning a fully
deterministic order (min difficulty, then subtopic name) with no
per-session variation, so every fresh session (which always starts at
the same difficulty) walked the identical subtopic sequence.
"""

import uuid

from sqlalchemy import func, select

from app.adaptive import topic_selector
from app.db.models import BankRound, QuestionBankItem, QuestionRound
from app.question_bank import selector


def test_subtopic_checklist_without_session_id_is_still_deterministic(db_session) -> None:
    """Callers that only need the *set* (e.g. completion_rules' coverage
    check) get the plain, stable order - order doesn't matter to them,
    but it shouldn't vary out from under them either."""
    first = topic_selector.get_subtopic_checklist(db_session, BankRound.PYTHON)
    second = topic_selector.get_subtopic_checklist(db_session, BankRound.PYTHON)
    assert first == second


def test_subtopic_checklist_order_is_stable_within_one_session(db_session) -> None:
    session_id = uuid.uuid4()
    first = topic_selector.get_subtopic_checklist(db_session, BankRound.PYTHON, session_id)
    second = topic_selector.get_subtopic_checklist(db_session, BankRound.PYTHON, session_id)
    assert first == second


def test_subtopic_checklist_order_differs_across_sessions(db_session) -> None:
    orders = {
        tuple(
            topic_selector.get_subtopic_checklist(
                db_session, BankRound.PYTHON, uuid.uuid4()
            )
        )
        for _ in range(15)
    }
    # Extremely unlikely (not impossible) for 15 independently-seeded
    # sessions to all land on the exact same shuffle by chance - this
    # confirms real variation, not a fluke.
    assert len(orders) > 1


def test_subtopic_checklist_preserves_easiest_difficulty_band_first(db_session) -> None:
    """Shuffling is scoped to within a difficulty band (two adjacent
    difficulty values) - a subtopic from a harder band must never be
    shuffled ahead of one from an easier band."""
    min_difficulty_by_subtopic = dict(
        db_session.execute(
            select(QuestionBankItem.subtopic, func.min(QuestionBankItem.difficulty))
            .where(QuestionBankItem.round == BankRound.PYTHON)
            .group_by(QuestionBankItem.subtopic)
        ).all()
    )

    for _ in range(10):
        checklist = topic_selector.get_subtopic_checklist(
            db_session, BankRound.PYTHON, uuid.uuid4()
        )
        bands = [(min_difficulty_by_subtopic[subtopic] - 1) // 2 for subtopic in checklist]
        assert bands == sorted(bands)


def test_subtopic_checklist_first_band_has_more_than_one_candidate(db_session) -> None:
    """The regression this whole module guards against: Python's seed
    data has exactly one subtopic at difficulty 1 ('data_types'), so a
    same-value tier (rather than a band pairing 1-2 together) left the
    very first question of the round identical across every session even
    after adding shuffling."""
    checklist = topic_selector.get_subtopic_checklist(db_session, BankRound.PYTHON, uuid.uuid4())
    min_difficulty_by_subtopic = dict(
        db_session.execute(
            select(QuestionBankItem.subtopic, func.min(QuestionBankItem.difficulty))
            .where(QuestionBankItem.round == BankRound.PYTHON)
            .group_by(QuestionBankItem.subtopic)
        ).all()
    )
    first_band = (min_difficulty_by_subtopic[checklist[0]] - 1) // 2
    candidates_in_first_band = [
        subtopic
        for subtopic in checklist
        if (min_difficulty_by_subtopic[subtopic] - 1) // 2 == first_band
    ]
    assert len(candidates_in_first_band) > 1


def test_first_bank_question_differs_across_sessions(db_session) -> None:
    """The actual end-to-end symptom: two freshly-created sessions, both
    starting at the same default difficulty, should not be handed the
    identical opening Python-round question every time."""
    picked_questions = set()
    for _ in range(15):
        session_id = uuid.uuid4()
        item = selector.select_next_bank_question(
            db_session,
            session_id,
            QuestionRound.PYTHON,
            BankRound.PYTHON,
            target_difficulty=2,
        )
        assert item is not None
        picked_questions.add(item.question_text)
    assert len(picked_questions) > 1
