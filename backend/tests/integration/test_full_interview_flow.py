"""Drives a full interview end to end through a stub AI Gateway, proving
the deterministic core (state machine, adaptive engine, scoring) works
without any real LLM calls - docs/BLUEPRINT.md §19 Phase 2 done criteria.
"""

from sqlalchemy import select

from app.ai.gateway import StubAIGateway
from app.db.models import (
    DifficultyChangeReason,
    DifficultyLog,
    InterviewQuestion,
    QuestionType,
    SessionState,
)
from app.orchestrator import state_machine

ALL_ROUNDS = {
    "INTRODUCTION",
    "PYTHON",
    "MACHINE_LEARNING",
    "NLP",
    "PROJECT_DISCUSSION",
    "SCENARIO",
    "HR",
}


def _strong_answer_for(question: InterviewQuestion) -> str:
    if question.question_bank_item is not None:
        concepts = question.question_bank_item.expected_concepts
        mentions = ", ".join(c.replace("_", " ") for c in concepts)
        return f"This answer thoroughly covers {mentions} with clear technical reasoning."
    return (
        "This is a thorough, substantive answer that explains my reasoning "
        "and experience in detail."
    )


def test_full_interview_reaches_completed_with_strong_answers(db_session) -> None:
    gateway = StubAIGateway()
    session = state_machine.create_session(db_session, display_name="Ada Lovelace")
    question = state_machine.start_session(db_session, gateway, session.id)

    max_turns = 200  # safety valve against an infinite-loop regression
    turns = 0
    while session.state not in (SessionState.COMPLETED, SessionState.TERMINATED):
        turns += 1
        assert turns <= max_turns, "interview did not terminate within a safe number of turns"
        transcript = _strong_answer_for(question)
        result = state_machine.submit_answer(
            db_session, gateway, session.id, question.id, transcript
        )
        session = result.session
        if result.next_question is None:
            break
        question = result.next_question

    assert session.state == SessionState.COMPLETED
    assert session.completed_at is not None

    rounds_seen = {
        row[0].value
        for row in db_session.execute(
            select(InterviewQuestion.round).where(InterviewQuestion.session_id == session.id)
        ).all()
    }
    assert rounds_seen == ALL_ROUNDS

    # Consistently strong answers should have pushed difficulty above the default.
    assert session.current_difficulty > 2

    difficulty_logs = (
        db_session.execute(select(DifficultyLog).where(DifficultyLog.session_id == session.id))
        .scalars()
        .all()
    )
    assert difficulty_logs
    assert all(log.reason == DifficultyChangeReason.STRONG_ANSWER for log in difficulty_logs)

    follow_ups = (
        db_session.execute(
            select(InterviewQuestion).where(
                InterviewQuestion.session_id == session.id,
                InterviewQuestion.question_type == QuestionType.FOLLOW_UP,
            )
        )
        .scalars()
        .all()
    )
    assert follow_ups, "strong, concept-mentioning answers should have triggered follow-ups"

    project_questions = (
        db_session.execute(
            select(InterviewQuestion).where(
                InterviewQuestion.session_id == session.id,
                InterviewQuestion.question_type == QuestionType.PROJECT,
            )
        )
        .scalars()
        .all()
    )
    assert project_questions, "project discussion should have generated top-level project questions"


def test_weak_answers_decrease_difficulty_and_skip_followups(db_session) -> None:
    gateway = StubAIGateway()
    session = state_machine.create_session(db_session)
    question = state_machine.start_session(db_session, gateway, session.id)

    while session.state == SessionState.INTRODUCTION:
        result = state_machine.submit_answer(
            db_session,
            gateway,
            session.id,
            question.id,
            "I am a student interested in machine learning.",
        )
        session = result.session
        question = result.next_question

    assert session.state == SessionState.PYTHON
    starting_difficulty = session.current_difficulty

    result = state_machine.submit_answer(db_session, gateway, session.id, question.id, "idk")
    session = result.session
    next_question = result.next_question

    assert session.current_difficulty < starting_difficulty

    logs = (
        db_session.execute(select(DifficultyLog).where(DifficultyLog.session_id == session.id))
        .scalars()
        .all()
    )
    assert logs[-1].reason == DifficultyChangeReason.WEAK_ANSWER
    assert next_question.question_type != QuestionType.FOLLOW_UP
