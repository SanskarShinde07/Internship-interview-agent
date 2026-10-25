import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics.engine import compute_analytics
from app.api.deps import get_db
from app.api.schemas import AnalyticsResponse
from app.db.models import InterviewSession, SessionState
from app.orchestrator.state_machine import InvalidTransitionError, SessionNotFoundError

router = APIRouter(prefix="/sessions", tags=["analytics"])

_FINISHED_STATES = (SessionState.COMPLETED, SessionState.TERMINATED)


@router.get("/{session_id}/analytics", response_model=AnalyticsResponse)
def get_analytics(session_id: uuid.UUID, db: Session = Depends(get_db)) -> AnalyticsResponse:
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise SessionNotFoundError(f"session {session_id} not found")
    if session.state not in _FINISHED_STATES:
        raise InvalidTransitionError("interview is not yet completed")

    analytics = compute_analytics(db, session_id)
    return AnalyticsResponse(**asdict(analytics))
