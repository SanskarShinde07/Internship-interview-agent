from datetime import UTC, datetime, timedelta

from app.analytics.engine import compute_analytics
from app.db.models import (
    AnswerEvaluation,
    CandidateAnswer,
    DifficultyChangeReason,
    DifficultyLog,
    InterviewQuestion,
    InterviewSession,
    QuestionRound,
    QuestionType,
    SessionState,
)


def test_compute_analytics_on_hand_built_session(db_session) -> None:
    session = InterviewSession(
        state=SessionState.COMPLETED,
        current_difficulty=3,
        started_at=datetime.now(UTC) - timedelta(minutes=10),
        completed_at=datetime.now(UTC),
    )
    db_session.add(session)
    db_session.flush()

    q1 = InterviewQuestion(
        session_id=session.id,
        round=QuestionRound.PYTHON,
        topic="fundamentals",
        difficulty=2,
        sequence_number=1,
        question_type=QuestionType.BANK,
        question_text="q1",
    )
    q2 = InterviewQuestion(
        session_id=session.id,
        round=QuestionRound.PYTHON,
        topic="oop",
        difficulty=3,
        sequence_number=2,
        question_type=QuestionType.BANK,
        question_text="q2",
    )
    db_session.add_all([q1, q2])
    db_session.flush()

    a1 = CandidateAnswer(
        interview_question_id=q1.id, transcript_text="answer one here", word_count=3
    )
    a2 = CandidateAnswer(
        interview_question_id=q2.id, transcript_text="a short answer", word_count=3
    )
    db_session.add_all([a1, a2])
    db_session.flush()

    e1 = AnswerEvaluation(
        candidate_answer_id=a1.id,
        technical_accuracy=90,
        relevance=90,
        completeness=90,
        communication_clarity=90,
        concept_coverage=90,
        composite_score=90,
        evaluator_reasoning="",
    )
    e2 = AnswerEvaluation(
        candidate_answer_id=a2.id,
        technical_accuracy=40,
        relevance=40,
        completeness=40,
        communication_clarity=40,
        concept_coverage=40,
        composite_score=40,
        evaluator_reasoning="",
    )
    db_session.add_all([e1, e2])

    db_session.add(
        DifficultyLog(
            session_id=session.id,
            sequence_number=2,
            previous_difficulty=2,
            new_difficulty=3,
            reason=DifficultyChangeReason.STRONG_ANSWER,
        )
    )
    db_session.commit()

    analytics = compute_analytics(db_session, session.id)

    assert analytics.total_questions == 2
    assert analytics.questions_per_round == {"PYTHON": 2}
    assert analytics.follow_up_questions == 0
    assert analytics.highest_difficulty_reached == 3
    assert analytics.topic_wise_scores == {"fundamentals": 90.0, "oop": 40.0}
    assert analytics.strongest_topic == "fundamentals"
    assert analytics.weakest_topic == "oop"
    assert analytics.average_technical_score == 65.0
    assert analytics.average_communication_score == 65.0
    assert analytics.average_answer_length == 3.0
    assert analytics.adaptive_difficulty_changes == 1
    assert analytics.interview_completion_rate == 1.0
    assert analytics.interview_duration_seconds is not None
    assert analytics.interview_duration_seconds > 0
    assert len(analytics.interview_timeline) == 2
