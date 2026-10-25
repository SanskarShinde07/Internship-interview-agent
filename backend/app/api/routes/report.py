import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.gateway import AIGateway
from app.api.deps import get_db, get_gateway
from app.api.schemas import ReportResponse
from app.db.models import InterviewSession, SessionState
from app.orchestrator.state_machine import InvalidTransitionError, SessionNotFoundError
from app.reports.generator import generate_report

router = APIRouter(prefix="/sessions", tags=["report"])

_FINISHED_STATES = (SessionState.COMPLETED, SessionState.TERMINATED)


@router.get("/{session_id}/report", response_model=ReportResponse)
def get_report(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    gateway: AIGateway = Depends(get_gateway),
) -> ReportResponse:
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise SessionNotFoundError(f"session {session_id} not found")
    if session.state not in _FINISHED_STATES:
        raise InvalidTransitionError("interview is not yet completed")

    report = generate_report(db, gateway, session_id)
    return ReportResponse(
        overall_score=report.overall_score,
        category_scores=report.category_scores,
        strengths=report.strengths,
        improvements=report.improvements,
        recruiter_summary=report.recruiter_summary,
        learning_roadmap=report.learning_roadmap,
        readiness_level=report.readiness_level.value,
    )
