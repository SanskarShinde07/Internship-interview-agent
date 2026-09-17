"""Data-deletion capability (docs/BLUEPRINT.md §17): a candidate can have
their session and everything derived from it permanently removed.
"""

import uuid

from sqlalchemy import func, select

from app.db.models import (
    AnswerEvaluation,
    Candidate,
    CandidateAnswer,
    CoachMessage,
    InterviewQuestion,
    InterviewSession,
)


def test_delete_session_removes_session_and_all_derived_rows(api_context) -> None:
    client = api_context.client
    db = api_context.session_factory()

    create_resp = client.post(
        "/api/v1/sessions", json={"display_name": "Delete Me", "email": "delete@example.com"}
    )
    session_id = create_resp.json()["session_id"]
    session_uuid = uuid.UUID(session_id)
    session = db.get(InterviewSession, session_uuid)
    candidate_id = session.candidate_id
    assert candidate_id is not None

    question = client.post(f"/api/v1/sessions/{session_id}/start").json()["current_question"]
    client.post(
        f"/api/v1/sessions/{session_id}/answer",
        json={"question_id": question["question_id"], "transcript_text": "an answer"},
    )
    db.expire_all()

    assert (
        db.execute(
            select(func.count())
            .select_from(InterviewQuestion)
            .where(InterviewQuestion.session_id == session_uuid)
        ).scalar_one()
        > 0
    )

    delete_resp = client.delete(f"/api/v1/sessions/{session_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 404

    db.expire_all()
    assert db.get(InterviewSession, session_uuid) is None
    assert db.get(Candidate, candidate_id) is None
    assert (
        db.execute(
            select(func.count())
            .select_from(InterviewQuestion)
            .where(InterviewQuestion.session_id == session_uuid)
        ).scalar_one()
        == 0
    )
    assert (
        db.execute(select(func.count()).select_from(CandidateAnswer)).scalar_one() == 0
    )
    assert (
        db.execute(select(func.count()).select_from(AnswerEvaluation)).scalar_one() == 0
    )
    assert db.execute(select(func.count()).select_from(CoachMessage)).scalar_one() == 0

    db.close()


def test_delete_unknown_session_returns_404(api_context) -> None:
    resp = api_context.client.delete(f"/api/v1/sessions/{uuid.uuid4()}")
    assert resp.status_code == 404
