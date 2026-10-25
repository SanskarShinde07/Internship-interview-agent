"""Post-Interview Coach service (docs/BLUEPRINT.md §2, §9).

Retrieval here is a deterministic lookup, not a vector search: either the
specific question/answer/evaluation the candidate referenced, or their
overall report (generated on demand if they go straight to the coach
without visiting the report page first). The corpus per session is small
enough that this is sufficient - see §9's own reasoning for skipping
retrieval infrastructure in V1.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gateway import AIGateway
from app.db.models import (
    AnswerEvaluation,
    CandidateAnswer,
    CoachConversation,
    CoachMessage,
    InterviewQuestion,
    MessageRole,
)
from app.reports.generator import generate_report


def _get_or_create_conversation(db: Session, session_id: uuid.UUID) -> CoachConversation:
    existing = db.execute(
        select(CoachConversation)
        .where(CoachConversation.session_id == session_id)
        .order_by(CoachConversation.created_at)
    ).scalars().first()
    if existing is not None:
        return existing

    conversation = CoachConversation(session_id=session_id)
    db.add(conversation)
    db.flush()
    return conversation


def _build_question_context(db: Session, question_id: uuid.UUID) -> str | None:
    question = db.get(InterviewQuestion, question_id)
    if question is None:
        return None

    answer = db.execute(
        select(CandidateAnswer).where(CandidateAnswer.interview_question_id == question_id)
    ).scalar_one_or_none()
    if answer is None:
        return f"Question: {question.question_text}\n(The candidate did not answer this question.)"

    evaluation = db.execute(
        select(AnswerEvaluation).where(AnswerEvaluation.candidate_answer_id == answer.id)
    ).scalar_one_or_none()

    lines = [
        f"Question ({question.round.value}, topic: {question.topic}): {question.question_text}",
        f"Candidate's answer: {answer.transcript_text}",
    ]
    if evaluation is not None:
        lines.append(
            f"Scores - technical_accuracy: {evaluation.technical_accuracy}, "
            f"relevance: {evaluation.relevance}, completeness: {evaluation.completeness}, "
            f"communication_clarity: {evaluation.communication_clarity}, "
            f"concept_coverage: {evaluation.concept_coverage}, "
            f"composite: {evaluation.composite_score}"
        )
        lines.append(f"Evaluator's reasoning: {evaluation.evaluator_reasoning}")
    return "\n".join(lines)


def _build_general_context(db: Session, gateway: AIGateway, session_id: uuid.UUID) -> str:
    report = generate_report(db, gateway, session_id)
    lines = [
        f"Overall score: {report.overall_score}/100 ({report.readiness_level.value})",
        f"Category scores: {report.category_scores}",
        f"Strengths: {'; '.join(report.strengths)}",
        f"Areas for improvement: {'; '.join(report.improvements)}",
        f"Recruiter summary: {report.recruiter_summary}",
    ]
    return "\n".join(lines)


def ask_coach(
    db: Session,
    gateway: AIGateway,
    session_id: uuid.UUID,
    message: str,
    referenced_question_id: uuid.UUID | None = None,
) -> tuple[str, uuid.UUID]:
    conversation = _get_or_create_conversation(db, session_id)

    db.add(
        CoachMessage(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=message,
            referenced_question_id=referenced_question_id,
        )
    )
    db.flush()

    context_text = None
    if referenced_question_id is not None:
        context_text = _build_question_context(db, referenced_question_id)
    if context_text is None:
        context_text = _build_general_context(db, gateway, session_id)

    reply_output = gateway.coach_reply(candidate_message=message, context_text=context_text)

    db.add(
        CoachMessage(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=reply_output.reply,
            referenced_question_id=referenced_question_id,
        )
    )
    db.commit()

    return reply_output.reply, conversation.id


def list_messages(db: Session, session_id: uuid.UUID) -> list[CoachMessage]:
    conversation = db.execute(
        select(CoachConversation).where(CoachConversation.session_id == session_id)
    ).scalar_one_or_none()
    if conversation is None:
        return []

    return list(
        db.execute(
            select(CoachMessage)
            .where(CoachMessage.conversation_id == conversation.id)
            .order_by(CoachMessage.created_at)
        )
        .scalars()
        .all()
    )
