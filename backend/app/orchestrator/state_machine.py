"""Interview Orchestrator (docs/BLUEPRINT.md §2, §3, §7).

Owns the interview state machine end to end. This module is the only
writer of `InterviewSession.state`. It calls the Adaptive Engine for
every decision that matters (difficulty, follow-up eligibility, round
completion) and the AI Gateway only for language generation and
evaluation - the gateway never decides what happens next.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.adaptive.completion_rules import is_round_complete, session_should_terminate_for_limits
from app.adaptive.difficulty import classify_score, next_difficulty, reason_for_band
from app.adaptive.followup_policy import is_followup_eligible, is_near_duplicate_question
from app.ai.gateway import AIGateway
from app.ai.schemas import InterviewerMode
from app.config import get_settings
from app.db.models import (
    AnswerEvaluation,
    BankRound,
    Candidate,
    CandidateAnswer,
    CoachConversation,
    CoachMessage,
    DifficultyLog,
    InterviewQuestion,
    InterviewReport,
    InterviewSession,
    QuestionRound,
    QuestionType,
    SessionState,
)
from app.orchestrator.round_controller import (
    MAX_TOP_LEVEL_PROJECTS,
    ROUND_ORDER,
    get_round_config,
)
from app.question_bank.selector import select_next_bank_question
from app.scoring.question_score import compute_composite_score


class OrchestratorError(Exception):
    pass


class SessionNotFoundError(OrchestratorError):
    pass


class InvalidTransitionError(OrchestratorError):
    pass


class QuestionMismatchError(OrchestratorError):
    pass


@dataclass
class AnswerResult:
    session: InterviewSession
    next_question: InterviewQuestion | None


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _get_session(db: Session, session_id: uuid.UUID) -> InterviewSession:
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise SessionNotFoundError(f"session {session_id} not found")
    return session


def create_session(
    db: Session,
    *,
    display_name: str | None = None,
    email: str | None = None,
    user_id: uuid.UUID | None = None,
) -> InterviewSession:
    candidate_id = None
    if display_name or email or user_id:
        candidate = Candidate(display_name=display_name, email=email, user_id=user_id)
        db.add(candidate)
        db.flush()
        candidate_id = candidate.id

    session = InterviewSession(candidate_id=candidate_id, state=SessionState.CREATED)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_current_question(db: Session, session_id: uuid.UUID) -> InterviewQuestion | None:
    _get_session(db, session_id)
    return (
        db.execute(
            select(InterviewQuestion)
            .outerjoin(
                CandidateAnswer, CandidateAnswer.interview_question_id == InterviewQuestion.id
            )
            .where(InterviewQuestion.session_id == session_id, CandidateAnswer.id.is_(None))
            .order_by(InterviewQuestion.sequence_number.desc())
        )
        .scalars()
        .first()
    )


def start_session(db: Session, gateway: AIGateway, session_id: uuid.UUID) -> InterviewQuestion:
    session = _get_session(db, session_id)
    if session.state != SessionState.CREATED:
        raise InvalidTransitionError(f"session {session_id} already started")

    session.state = SessionState.INTRODUCTION
    session.started_at = _utcnow()
    db.flush()

    question = _advance(
        db, gateway, session, prev_question=None, composite_score=None, mentioned_concepts=[]
    )
    db.commit()
    if question is None:
        raise OrchestratorError("failed to generate the opening question")
    return question


def submit_answer(
    db: Session,
    gateway: AIGateway,
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    transcript_text: str,
    duration_seconds: float | None = None,
) -> AnswerResult:
    session = _get_session(db, session_id)
    if session.state in (SessionState.COMPLETED, SessionState.TERMINATED):
        raise InvalidTransitionError(f"session {session_id} already finished")

    question = db.get(InterviewQuestion, question_id)
    if question is None or question.session_id != session.id:
        raise QuestionMismatchError("question does not belong to this session")

    current_question = get_current_question(db, session_id)
    if current_question is None or current_question.id != question.id:
        raise QuestionMismatchError("question is not the session's current pending question")

    answer = CandidateAnswer(
        interview_question_id=question.id,
        transcript_text=transcript_text,
        answer_duration_seconds=duration_seconds,
        word_count=len(transcript_text.split()),
    )
    db.add(answer)
    db.flush()

    config = get_round_config(session.state)
    composite_score: int | None = None
    mentioned_concepts: list[str] = []

    if config.scored:
        expected_concepts = (
            question.question_bank_item.expected_concepts if question.question_bank_item else []
        )
        eval_output = gateway.evaluate_answer(
            question_text=question.question_text,
            expected_concepts=expected_concepts,
            transcript_text=transcript_text,
        )
        composite_score = compute_composite_score(eval_output)
        db.add(
            AnswerEvaluation(
                candidate_answer_id=answer.id,
                technical_accuracy=eval_output.technical_accuracy,
                relevance=eval_output.relevance,
                completeness=eval_output.completeness,
                communication_clarity=eval_output.communication_clarity,
                concept_coverage=eval_output.concept_coverage,
                composite_score=composite_score,
                evaluator_reasoning=eval_output.reasoning,
                flags=["evaluation_fallback"] if eval_output.fallback else None,
            )
        )
        mentioned_concepts = eval_output.mentioned_concepts

        band = classify_score(composite_score)
        new_difficulty = next_difficulty(session.current_difficulty, band)
        if new_difficulty != session.current_difficulty:
            db.add(
                DifficultyLog(
                    session_id=session.id,
                    sequence_number=question.sequence_number,
                    previous_difficulty=session.current_difficulty,
                    new_difficulty=new_difficulty,
                    reason=reason_for_band(band),
                )
            )
            session.current_difficulty = new_difficulty

    db.flush()

    settings = get_settings()
    should_terminate, reason = session_should_terminate_for_limits(
        total_questions_in_session=_count_total_questions(db, session.id),
        started_at=session.started_at,
        max_questions_per_session=settings.max_questions_per_session,
        max_session_duration_minutes=settings.max_session_duration_minutes,
    )
    if should_terminate:
        session.state = SessionState.TERMINATED
        session.termination_reason = reason
        session.completed_at = _utcnow()
        db.commit()
        return AnswerResult(session=session, next_question=None)

    next_question = _advance(
        db,
        gateway,
        session,
        prev_question=question,
        composite_score=composite_score,
        mentioned_concepts=mentioned_concepts,
    )
    db.commit()
    return AnswerResult(session=session, next_question=next_question)


def end_session(
    db: Session, session_id: uuid.UUID, reason: str | None = None
) -> InterviewSession:
    session = _get_session(db, session_id)
    if session.state in (SessionState.COMPLETED, SessionState.TERMINATED):
        raise InvalidTransitionError(f"session {session_id} already finished")

    session.state = SessionState.TERMINATED
    session.termination_reason = reason or "candidate_ended"
    session.completed_at = _utcnow()
    db.commit()
    return session


def delete_session(db: Session, session_id: uuid.UUID) -> None:
    """Permanently deletes a session and everything derived from it
    (docs/BLUEPRINT.md §17: candidates can request their data be deleted).
    Also removes the session's exclusively-owned candidate row, if any -
    each session creates its own Candidate rather than reusing one, so
    there's nothing else that could still need it.
    """
    session = _get_session(db, session_id)

    question_ids = select(InterviewQuestion.id).where(InterviewQuestion.session_id == session_id)
    answer_ids = select(CandidateAnswer.id).where(
        CandidateAnswer.interview_question_id.in_(question_ids)
    )
    conversation_ids = select(CoachConversation.id).where(
        CoachConversation.session_id == session_id
    )

    db.execute(delete(CoachMessage).where(CoachMessage.conversation_id.in_(conversation_ids)))
    db.execute(delete(CoachConversation).where(CoachConversation.session_id == session_id))
    db.execute(delete(AnswerEvaluation).where(AnswerEvaluation.candidate_answer_id.in_(answer_ids)))
    db.execute(delete(CandidateAnswer).where(CandidateAnswer.interview_question_id.in_(question_ids)))
    db.execute(delete(InterviewQuestion).where(InterviewQuestion.session_id == session_id))
    db.execute(delete(DifficultyLog).where(DifficultyLog.session_id == session_id))
    db.execute(delete(InterviewReport).where(InterviewReport.session_id == session_id))

    candidate_id = session.candidate_id
    db.delete(session)
    if candidate_id is not None:
        candidate = db.get(Candidate, candidate_id)
        if candidate is not None:
            db.delete(candidate)

    db.commit()


def _advance(
    db: Session,
    gateway: AIGateway,
    session: InterviewSession,
    *,
    prev_question: InterviewQuestion | None,
    composite_score: int | None,
    mentioned_concepts: list[str],
) -> InterviewQuestion | None:
    round_ = QuestionRound(session.state.value)
    config = get_round_config(session.state)

    if prev_question is not None and is_round_complete(
        db,
        session.id,
        round_,
        min_questions=config.min_questions,
        max_questions=config.max_questions,
        uses_bank=config.uses_bank,
    ):
        return _transition_to_next_round(db, gateway, session)

    if config.scored and prev_question is not None and composite_score is not None:
        followups_used = _count_followups_for_topic(db, session.id, prev_question.topic)
        decision = is_followup_eligible(
            round_=round_,
            composite_score=composite_score,
            mentioned_concepts=mentioned_concepts,
            followups_used_for_topic=followups_used,
            max_followups_per_topic=config.max_followups_per_topic,
        )
        if decision.eligible:
            output = gateway.phrase_question(
                mode=InterviewerMode.FOLLOW_UP, directive=decision.concept
            )
            if not is_near_duplicate_question(
                output.spoken_text, _previous_question_texts(db, session.id)
            ):
                return _create_question(
                    db,
                    session,
                    round_,
                    topic=prev_question.topic,
                    sequence_number=_next_sequence_number(db, session.id),
                    question_type=QuestionType.FOLLOW_UP,
                    question_text=output.spoken_text,
                    parent_question_id=prev_question.id,
                )

    if config.uses_bank:
        bank_round = BankRound(round_.value)
        item = select_next_bank_question(
            db, session.id, round_, bank_round, session.current_difficulty
        )
        if item is not None:
            return _create_question(
                db,
                session,
                round_,
                topic=item.topic,
                sequence_number=_next_sequence_number(db, session.id),
                question_type=QuestionType.BANK,
                question_text=item.question_text,
                question_bank_item_id=item.id,
            )
    elif round_ == QuestionRound.PROJECT_DISCUSSION:
        project_count = _count_top_level_project_questions(db, session.id)
        asked_in_round = _count_questions_in_round(db, session.id, round_)
        if project_count < MAX_TOP_LEVEL_PROJECTS and asked_in_round < config.max_questions:
            directive = f"project_{project_count + 1}"
            output = gateway.phrase_question(mode=InterviewerMode.PROJECT, directive=directive)
            return _create_question(
                db,
                session,
                round_,
                topic=directive,
                sequence_number=_next_sequence_number(db, session.id),
                question_type=QuestionType.PROJECT,
                question_text=output.spoken_text,
            )
    elif round_ == QuestionRound.INTRODUCTION:
        asked_in_round = _count_questions_in_round(db, session.id, round_)
        if asked_in_round < config.max_questions:
            output = gateway.phrase_question(
                mode=InterviewerMode.INTRO, directive=f"turn_{asked_in_round + 1}"
            )
            return _create_question(
                db,
                session,
                round_,
                topic="introduction",
                sequence_number=_next_sequence_number(db, session.id),
                question_type=QuestionType.INTRO,
                question_text=output.spoken_text,
            )

    return _transition_to_next_round(db, gateway, session)


def _transition_to_next_round(
    db: Session, gateway: AIGateway, session: InterviewSession
) -> InterviewQuestion | None:
    current_index = ROUND_ORDER.index(session.state)
    if current_index + 1 >= len(ROUND_ORDER):
        session.state = SessionState.COMPLETED
        session.completed_at = _utcnow()
        db.flush()
        return None

    session.state = ROUND_ORDER[current_index + 1]
    db.flush()
    return _advance(
        db, gateway, session, prev_question=None, composite_score=None, mentioned_concepts=[]
    )


def _create_question(
    db: Session,
    session: InterviewSession,
    round_: QuestionRound,
    *,
    topic: str,
    sequence_number: int,
    question_type: QuestionType,
    question_text: str,
    question_bank_item_id: uuid.UUID | None = None,
    parent_question_id: uuid.UUID | None = None,
) -> InterviewQuestion:
    question = InterviewQuestion(
        session_id=session.id,
        question_bank_item_id=question_bank_item_id,
        parent_question_id=parent_question_id,
        round=round_,
        topic=topic,
        difficulty=session.current_difficulty,
        sequence_number=sequence_number,
        question_type=question_type,
        question_text=question_text,
    )
    db.add(question)
    db.flush()
    return question


def _count_total_questions(db: Session, session_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(InterviewQuestion)
        .where(InterviewQuestion.session_id == session_id)
    ).scalar_one()


def _count_questions_in_round(db: Session, session_id: uuid.UUID, round_: QuestionRound) -> int:
    return db.execute(
        select(func.count())
        .select_from(InterviewQuestion)
        .where(InterviewQuestion.session_id == session_id, InterviewQuestion.round == round_)
    ).scalar_one()


def _next_sequence_number(db: Session, session_id: uuid.UUID) -> int:
    return _count_total_questions(db, session_id) + 1


def _count_followups_for_topic(db: Session, session_id: uuid.UUID, topic: str) -> int:
    return db.execute(
        select(func.count())
        .select_from(InterviewQuestion)
        .where(
            InterviewQuestion.session_id == session_id,
            InterviewQuestion.topic == topic,
            InterviewQuestion.question_type == QuestionType.FOLLOW_UP,
        )
    ).scalar_one()


def _count_top_level_project_questions(db: Session, session_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(InterviewQuestion)
        .where(
            InterviewQuestion.session_id == session_id,
            InterviewQuestion.question_type == QuestionType.PROJECT,
        )
    ).scalar_one()


def _previous_question_texts(db: Session, session_id: uuid.UUID) -> list[str]:
    rows = db.execute(
        select(InterviewQuestion.question_text).where(InterviewQuestion.session_id == session_id)
    ).all()
    return [row[0] for row in rows]
