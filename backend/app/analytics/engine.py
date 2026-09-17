"""Analytics Engine (docs/BLUEPRINT.md §14).

Every metric here is computed directly from stored rows - no LLM
involvement, ever. This is what "don't let the LLM invent analytics"
means in practice.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AnswerEvaluation,
    CandidateAnswer,
    DifficultyLog,
    InterviewQuestion,
    InterviewSession,
    QuestionType,
    SessionState,
)
from app.orchestrator.round_controller import ROUND_CONFIGS


@dataclass
class DifficultyChange:
    sequence_number: int
    previous_difficulty: int
    new_difficulty: int
    reason: str


@dataclass
class TimelineEntry:
    sequence_number: int
    round: str
    topic: str
    difficulty: int
    question_type: str


@dataclass
class AnalyticsResult:
    interview_duration_seconds: float | None
    total_questions: int
    questions_per_round: dict[str, int]
    follow_up_questions: int
    difficulty_progression: list[DifficultyChange]
    highest_difficulty_reached: int | None
    topic_wise_scores: dict[str, float]
    average_technical_score: float | None
    average_communication_score: float | None
    average_answer_length: float | None
    strongest_topic: str | None
    weakest_topic: str | None
    round_completion_times_seconds: dict[str, float]
    interview_completion_rate: float
    adaptive_difficulty_changes: int
    interview_timeline: list[TimelineEntry] = field(default_factory=list)


_EXPECTED_TOTAL_QUESTIONS = sum(config.min_questions for config in ROUND_CONFIGS.values())


def compute_analytics(db: Session, session_id: uuid.UUID) -> AnalyticsResult:
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise ValueError(f"session {session_id} not found")

    questions = (
        db.execute(
            select(InterviewQuestion)
            .where(InterviewQuestion.session_id == session_id)
            .order_by(InterviewQuestion.sequence_number)
        )
        .scalars()
        .all()
    )
    total_questions = len(questions)

    questions_per_round: dict[str, int] = {}
    for question in questions:
        questions_per_round[question.round.value] = (
            questions_per_round.get(question.round.value, 0) + 1
        )

    follow_up_questions = sum(1 for q in questions if q.question_type == QuestionType.FOLLOW_UP)
    highest_difficulty_reached = max((q.difficulty for q in questions), default=None)

    difficulty_rows = (
        db.execute(
            select(DifficultyLog)
            .where(DifficultyLog.session_id == session_id)
            .order_by(DifficultyLog.sequence_number)
        )
        .scalars()
        .all()
    )
    difficulty_progression = [
        DifficultyChange(
            sequence_number=row.sequence_number,
            previous_difficulty=row.previous_difficulty,
            new_difficulty=row.new_difficulty,
            reason=row.reason.value,
        )
        for row in difficulty_rows
    ]

    topic_score_rows = db.execute(
        select(InterviewQuestion.topic, func.avg(AnswerEvaluation.composite_score))
        .join(CandidateAnswer, CandidateAnswer.interview_question_id == InterviewQuestion.id)
        .join(AnswerEvaluation, AnswerEvaluation.candidate_answer_id == CandidateAnswer.id)
        .where(InterviewQuestion.session_id == session_id)
        .group_by(InterviewQuestion.topic)
    ).all()
    topic_wise_scores = {topic: round(score, 1) for topic, score in topic_score_rows}

    strongest_topic = max(topic_wise_scores, key=topic_wise_scores.get, default=None)
    weakest_topic = min(topic_wise_scores, key=topic_wise_scores.get, default=None)

    round_completion_times_seconds: dict[str, float] = {}
    asked_at_by_round: dict[str, list] = {}
    for q in questions:
        asked_at_by_round.setdefault(q.round.value, []).append(q.asked_at)
    for round_name, timestamps in asked_at_by_round.items():
        round_completion_times_seconds[round_name] = (
            max(timestamps) - min(timestamps)
        ).total_seconds()

    avg_technical, avg_communication = db.execute(
        select(
            func.avg(AnswerEvaluation.technical_accuracy),
            func.avg(AnswerEvaluation.communication_clarity),
        )
        .join(CandidateAnswer, CandidateAnswer.id == AnswerEvaluation.candidate_answer_id)
        .join(InterviewQuestion, InterviewQuestion.id == CandidateAnswer.interview_question_id)
        .where(InterviewQuestion.session_id == session_id)
    ).one()

    avg_answer_length = db.execute(
        select(func.avg(CandidateAnswer.word_count))
        .join(InterviewQuestion, InterviewQuestion.id == CandidateAnswer.interview_question_id)
        .where(InterviewQuestion.session_id == session_id)
    ).scalar_one()

    duration_seconds = None
    if session.started_at and session.completed_at:
        duration_seconds = (session.completed_at - session.started_at).total_seconds()

    if session.state == SessionState.COMPLETED:
        completion_rate = 1.0
    else:
        completion_rate = min(1.0, total_questions / _EXPECTED_TOTAL_QUESTIONS)

    timeline = [
        TimelineEntry(
            sequence_number=q.sequence_number,
            round=q.round.value,
            topic=q.topic,
            difficulty=q.difficulty,
            question_type=q.question_type.value,
        )
        for q in questions
    ]

    return AnalyticsResult(
        interview_duration_seconds=duration_seconds,
        total_questions=total_questions,
        questions_per_round=questions_per_round,
        follow_up_questions=follow_up_questions,
        difficulty_progression=difficulty_progression,
        highest_difficulty_reached=highest_difficulty_reached,
        topic_wise_scores=topic_wise_scores,
        average_technical_score=round(avg_technical, 1) if avg_technical is not None else None,
        average_communication_score=(
            round(avg_communication, 1) if avg_communication is not None else None
        ),
        average_answer_length=(
            round(avg_answer_length, 1) if avg_answer_length is not None else None
        ),
        strongest_topic=strongest_topic,
        weakest_topic=weakest_topic,
        round_completion_times_seconds=round_completion_times_seconds,
        interview_completion_rate=completion_rate,
        adaptive_difficulty_changes=len(difficulty_progression),
        interview_timeline=timeline,
    )
