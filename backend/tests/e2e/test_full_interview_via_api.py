"""Drives a full interview through HTTP only - the API-layer equivalent
of docs/BLUEPRINT.md §19 Phase 4's "Postman/HTTPie-driven manual
walkthrough", automated instead of manual, plus the report/analytics/
coach endpoints that Phase 4 pulled forward.
"""

import uuid

from app.db.models import InterviewQuestion

MAX_TURNS = 200


def _strong_answer_for(lookup_db, question_id: str) -> str:
    question = lookup_db.get(InterviewQuestion, uuid.UUID(question_id))
    if question is not None and question.question_bank_item is not None:
        concepts = question.question_bank_item.expected_concepts
        mentions = ", ".join(c.replace("_", " ") for c in concepts)
        return f"This answer thoroughly covers {mentions} with clear technical reasoning."
    return (
        "This is a thorough, substantive answer that explains my reasoning "
        "and experience in detail."
    )


def test_full_interview_via_http_reaches_completed_report_and_coach(api_context) -> None:
    client = api_context.client
    lookup_db = api_context.session_factory()

    create_resp = client.post("/api/v1/sessions", json={"display_name": "Ada Lovelace"})
    assert create_resp.status_code == 201
    session_id = create_resp.json()["session_id"]
    assert create_resp.json()["state"] == "CREATED"

    start_resp = client.post(f"/api/v1/sessions/{session_id}/start")
    assert start_resp.status_code == 200
    body = start_resp.json()
    assert body["state"] == "INTRODUCTION"
    question = body["current_question"]

    for _ in range(MAX_TURNS):
        transcript = _strong_answer_for(lookup_db, question["question_id"])
        answer_resp = client.post(
            f"/api/v1/sessions/{session_id}/answer",
            json={"question_id": question["question_id"], "transcript_text": transcript},
        )
        assert answer_resp.status_code == 200
        body = answer_resp.json()
        if body["next_question"] is None:
            break
        question = body["next_question"]
    else:
        raise AssertionError("interview did not complete within MAX_TURNS")

    assert body["state"] == "COMPLETED"

    session_resp = client.get(f"/api/v1/sessions/{session_id}")
    assert session_resp.status_code == 200
    assert session_resp.json()["state"] == "COMPLETED"

    report_resp = client.get(f"/api/v1/sessions/{session_id}/report")
    assert report_resp.status_code == 200
    report = report_resp.json()
    assert 0 <= report["overall_score"] <= 100
    assert report["readiness_level"] in {"NOT_READY", "DEVELOPING", "READY", "STRONG"}
    assert isinstance(report["strengths"], list) and report["strengths"]
    assert isinstance(report["learning_roadmap"], list)

    # Idempotent: a second fetch returns the same stored report, not a
    # freshly (and differently) generated one.
    report_resp_again = client.get(f"/api/v1/sessions/{session_id}/report")
    assert report_resp_again.json() == report

    analytics_resp = client.get(f"/api/v1/sessions/{session_id}/analytics")
    assert analytics_resp.status_code == 200
    analytics = analytics_resp.json()
    assert analytics["interview_completion_rate"] == 1.0
    assert analytics["total_questions"] > 0
    assert set(analytics["questions_per_round"].keys()) == {
        "INTRODUCTION",
        "PYTHON",
        "MACHINE_LEARNING",
        "NLP",
        "PROJECT_DISCUSSION",
        "SCENARIO",
        "HR",
    }

    coach_resp = client.post(
        f"/api/v1/sessions/{session_id}/coach/messages",
        json={"message": "What topics should I study next?"},
    )
    assert coach_resp.status_code == 200
    coach_body = coach_resp.json()
    assert coach_body["reply"]
    conversation_id = coach_body["conversation_id"]

    coach_history_resp = client.get(f"/api/v1/sessions/{session_id}/coach/messages")
    assert coach_history_resp.status_code == 200
    messages = coach_history_resp.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "USER"
    assert messages[1]["role"] == "ASSISTANT"

    # A second coach message reuses the same conversation.
    second_coach_resp = client.post(
        f"/api/v1/sessions/{session_id}/coach/messages",
        json={"message": "Can you explain overfitting?"},
    )
    assert second_coach_resp.json()["conversation_id"] == conversation_id

    lookup_db.close()
