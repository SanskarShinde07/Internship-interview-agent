"""Report Generator (docs/BLUEPRINT.md §2, §13).

Assembles the final recruiter report: deterministic scores from the
scoring/analytics modules, narrative text from exactly one Recruiter
Agent call. Idempotent per session - a second call returns the stored
report rather than calling the Recruiter Agent again.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gateway import AIGateway
from app.analytics.engine import compute_analytics
from app.db.models import (
    AnswerEvaluation,
    CandidateAnswer,
    InterviewQuestion,
    InterviewReport,
    InterviewSession,
    SessionState,
)
from app.scoring.overall_score import compute_overall_score, compute_readiness_level
from app.scoring.round_score import compute_average_score

STRONG_TOPIC_THRESHOLD = 80
WEAK_TOPIC_THRESHOLD = 50


def _round_scores(db: Session, session_id: uuid.UUID) -> dict[SessionState, float]:
    rows = db.execute(
        select(InterviewQuestion.round, AnswerEvaluation.composite_score)
        .join(CandidateAnswer, CandidateAnswer.interview_question_id == InterviewQuestion.id)
        .join(AnswerEvaluation, AnswerEvaluation.candidate_answer_id == CandidateAnswer.id)
        .where(InterviewQuestion.session_id == session_id)
    ).all()

    scores_by_round: dict[SessionState, list[int]] = {}
    for round_, score in rows:
        session_state = SessionState(round_.value)
        scores_by_round.setdefault(session_state, []).append(score)

    round_scores: dict[SessionState, float] = {}
    for round_state, scores in scores_by_round.items():
        average = compute_average_score(scores)
        if average is not None:
            round_scores[round_state] = average
    return round_scores


def generate_report(db: Session, gateway: AIGateway, session_id: uuid.UUID) -> InterviewReport:
    existing = db.execute(
        select(InterviewReport).where(InterviewReport.session_id == session_id)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    session = db.get(InterviewSession, session_id)
    if session is None:
        raise ValueError(f"session {session_id} not found")

    round_scores = _round_scores(db, session_id)
    overall_score = compute_overall_score(round_scores) or 0
    readiness_level = compute_readiness_level(overall_score)

    analytics = compute_analytics(db, session_id)

    category_scores = {
        "python": round_scores.get(SessionState.PYTHON),
        "machine_learning": round_scores.get(SessionState.MACHINE_LEARNING),
        "nlp": round_scores.get(SessionState.NLP),
        "problem_solving": round_scores.get(SessionState.SCENARIO),
        "communication": analytics.average_communication_score,
        "project_understanding": round_scores.get(SessionState.PROJECT_DISCUSSION),
    }

    strong_topics = [
        topic
        for topic, score in analytics.topic_wise_scores.items()
        if score >= STRONG_TOPIC_THRESHOLD
    ]
    weak_topics = [
        topic
        for topic, score in analytics.topic_wise_scores.items()
        if score < WEAK_TOPIC_THRESHOLD
    ]

    narrative = gateway.generate_recruiter_narrative(
        overall_score=overall_score,
        readiness_level=readiness_level.value,
        category_scores=category_scores,
        strong_topics=strong_topics,
        weak_topics=weak_topics,
    )

    report = InterviewReport(
        session_id=session_id,
        overall_score=overall_score,
        category_scores=category_scores,
        strengths=narrative.strengths,
        improvements=narrative.improvements,
        recruiter_summary=narrative.recruiter_summary,
        learning_roadmap=[item.model_dump() for item in narrative.learning_roadmap],
        readiness_level=readiness_level,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
