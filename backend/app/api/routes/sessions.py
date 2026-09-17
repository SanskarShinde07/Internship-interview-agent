import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.gateway import AIGateway
from app.api.deps import get_db, get_gateway
from app.api.schemas import (
    CreateSessionRequest,
    EndSessionRequest,
    EndSessionResponse,
    NextStepResponse,
    QuestionResponse,
    RepeatQuestionResponse,
    SessionProgressResponse,
    SessionSummaryResponse,
    StartSessionResponse,
    SubmitAnswerRequest,
)
from app.core.rate_limit import enforce_rate_limit
from app.db.models import InterviewQuestion, InterviewSession
from app.orchestrator import state_machine
from app.orchestrator.round_controller import expected_total_questions
from app.orchestrator.state_machine import InvalidTransitionError, SessionNotFoundError

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _to_question_response(question: InterviewQuestion) -> QuestionResponse:
    return QuestionResponse(
        question_id=question.id,
        question_text=question.question_text,
        round=question.round.value,
        difficulty=question.difficulty,
    )


@router.post("", response_model=SessionSummaryResponse, status_code=201)
def create_session(
    payload: CreateSessionRequest | None = None, db: Session = Depends(get_db)
) -> SessionSummaryResponse:
    session = state_machine.create_session(
        db,
        display_name=payload.display_name if payload else None,
        email=payload.email if payload else None,
    )
    return SessionSummaryResponse(session_id=session.id, state=session.state)


@router.post("/{session_id}/start", response_model=StartSessionResponse)
def start_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    gateway: AIGateway = Depends(get_gateway),
) -> StartSessionResponse:
    question = state_machine.start_session(db, gateway, session_id)
    session = db.get(InterviewSession, session_id)
    return StartSessionResponse(
        state=session.state, current_question=_to_question_response(question)
    )


@router.get("/{session_id}", response_model=SessionProgressResponse)
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db)) -> SessionProgressResponse:
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise SessionNotFoundError(f"session {session_id} not found")

    asked = db.execute(
        select(func.count())
        .select_from(InterviewQuestion)
        .where(InterviewQuestion.session_id == session_id)
    ).scalar_one()

    return SessionProgressResponse(
        state=session.state,
        round=session.state.value,
        difficulty=session.current_difficulty,
        progress={"asked": asked, "total_estimate": expected_total_questions()},
    )


@router.get("/{session_id}/current-question", response_model=QuestionResponse)
def get_current_question(
    session_id: uuid.UUID, db: Session = Depends(get_db)
) -> QuestionResponse:
    question = state_machine.get_current_question(db, session_id)
    if question is None:
        raise InvalidTransitionError("no active question for this session")
    return _to_question_response(question)


@router.post("/{session_id}/answer", response_model=NextStepResponse)
def submit_answer(
    session_id: uuid.UUID,
    payload: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    gateway: AIGateway = Depends(get_gateway),
    _rate_limit: None = Depends(enforce_rate_limit),
) -> NextStepResponse:
    result = state_machine.submit_answer(
        db,
        gateway,
        session_id,
        payload.question_id,
        payload.transcript_text,
        payload.duration_seconds,
    )
    next_question = (
        _to_question_response(result.next_question) if result.next_question else None
    )
    return NextStepResponse(state=result.session.state, next_question=next_question)


@router.post("/{session_id}/repeat-question", response_model=RepeatQuestionResponse)
def repeat_question(
    session_id: uuid.UUID, db: Session = Depends(get_db)
) -> RepeatQuestionResponse:
    question = state_machine.get_current_question(db, session_id)
    if question is None:
        raise InvalidTransitionError("no active question to repeat")
    return RepeatQuestionResponse(question_text=question.question_text)


@router.post("/{session_id}/end", response_model=EndSessionResponse)
def end_session(
    session_id: uuid.UUID,
    payload: EndSessionRequest | None = None,
    db: Session = Depends(get_db),
) -> EndSessionResponse:
    session = state_machine.end_session(db, session_id, payload.reason if payload else None)
    return EndSessionResponse(state=session.state)


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Permanently deletes this session and all data derived from it
    (docs/BLUEPRINT.md §17). Irreversible - there is no confirmation step
    at this layer; the frontend is responsible for confirming with the
    candidate before calling this.
    """
    state_machine.delete_session(db, session_id)
