import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.gateway import AIGateway
from app.api.deps import get_db, get_gateway
from app.api.schemas import (
    CoachMessageItem,
    CoachMessageRequest,
    CoachMessageResponse,
    CoachMessagesListResponse,
)
from app.coach.service import ask_coach, list_messages
from app.core.rate_limit import enforce_rate_limit
from app.db.models import InterviewSession, SessionState
from app.orchestrator.state_machine import InvalidTransitionError, SessionNotFoundError

router = APIRouter(prefix="/sessions", tags=["coach"])

_FINISHED_STATES = (SessionState.COMPLETED, SessionState.TERMINATED)


def _require_finished_session(db: Session, session_id: uuid.UUID) -> None:
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise SessionNotFoundError(f"session {session_id} not found")
    if session.state not in _FINISHED_STATES:
        raise InvalidTransitionError("interview is not yet completed")


@router.post("/{session_id}/coach/messages", response_model=CoachMessageResponse)
def post_coach_message(
    session_id: uuid.UUID,
    payload: CoachMessageRequest,
    db: Session = Depends(get_db),
    gateway: AIGateway = Depends(get_gateway),
    _rate_limit: None = Depends(enforce_rate_limit),
) -> CoachMessageResponse:
    _require_finished_session(db, session_id)
    reply, conversation_id = ask_coach(
        db, gateway, session_id, payload.message, payload.referenced_question_id
    )
    return CoachMessageResponse(reply=reply, conversation_id=conversation_id)


@router.get("/{session_id}/coach/messages", response_model=CoachMessagesListResponse)
def get_coach_messages(
    session_id: uuid.UUID, db: Session = Depends(get_db)
) -> CoachMessagesListResponse:
    _require_finished_session(db, session_id)
    messages = list_messages(db, session_id)
    return CoachMessagesListResponse(
        messages=[
            CoachMessageItem(
                role=m.role.value,
                content=m.content,
                referenced_question_id=m.referenced_question_id,
            )
            for m in messages
        ]
    )
