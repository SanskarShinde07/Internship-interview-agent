import uuid


def test_get_unknown_session_returns_404(api_context) -> None:
    resp = api_context.client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "session_not_found"


def test_starting_a_session_twice_returns_409(api_context) -> None:
    client = api_context.client
    session_id = client.post("/api/v1/sessions", json={}).json()["session_id"]

    first = client.post(f"/api/v1/sessions/{session_id}/start")
    assert first.status_code == 200

    second = client.post(f"/api/v1/sessions/{session_id}/start")
    assert second.status_code == 409
    assert second.json()["error_code"] == "invalid_transition"


def test_current_question_before_start_returns_409(api_context) -> None:
    client = api_context.client
    session_id = client.post("/api/v1/sessions", json={}).json()["session_id"]

    resp = client.get(f"/api/v1/sessions/{session_id}/current-question")
    assert resp.status_code == 409


def test_answer_with_empty_transcript_returns_422(api_context) -> None:
    client = api_context.client
    session_id = client.post("/api/v1/sessions", json={}).json()["session_id"]
    question = client.post(f"/api/v1/sessions/{session_id}/start").json()["current_question"]

    resp = client.post(
        f"/api/v1/sessions/{session_id}/answer",
        json={"question_id": question["question_id"], "transcript_text": ""},
    )
    assert resp.status_code == 422


def test_answer_with_oversized_transcript_returns_422(api_context) -> None:
    client = api_context.client
    session_id = client.post("/api/v1/sessions", json={}).json()["session_id"]
    question = client.post(f"/api/v1/sessions/{session_id}/start").json()["current_question"]

    resp = client.post(
        f"/api/v1/sessions/{session_id}/answer",
        json={"question_id": question["question_id"], "transcript_text": "x" * 4001},
    )
    assert resp.status_code == 422


def test_coach_message_with_oversized_text_returns_422(api_context) -> None:
    client = api_context.client
    session_id = client.post("/api/v1/sessions", json={}).json()["session_id"]
    client.post(f"/api/v1/sessions/{session_id}/start")
    client.post(f"/api/v1/sessions/{session_id}/end")

    resp = client.post(
        f"/api/v1/sessions/{session_id}/coach/messages",
        json={"message": "x" * 2001},
    )
    assert resp.status_code == 422


def test_answer_with_wrong_question_id_returns_400(api_context) -> None:
    client = api_context.client
    session_id = client.post("/api/v1/sessions", json={}).json()["session_id"]
    client.post(f"/api/v1/sessions/{session_id}/start")

    resp = client.post(
        f"/api/v1/sessions/{session_id}/answer",
        json={"question_id": str(uuid.uuid4()), "transcript_text": "some answer"},
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "question_mismatch"


def test_report_before_completion_returns_409(api_context) -> None:
    client = api_context.client
    session_id = client.post("/api/v1/sessions", json={}).json()["session_id"]
    client.post(f"/api/v1/sessions/{session_id}/start")

    resp = client.get(f"/api/v1/sessions/{session_id}/report")
    assert resp.status_code == 409


def test_analytics_before_completion_returns_409(api_context) -> None:
    client = api_context.client
    session_id = client.post("/api/v1/sessions", json={}).json()["session_id"]
    client.post(f"/api/v1/sessions/{session_id}/start")

    resp = client.get(f"/api/v1/sessions/{session_id}/analytics")
    assert resp.status_code == 409


def test_coach_before_completion_returns_409(api_context) -> None:
    client = api_context.client
    session_id = client.post("/api/v1/sessions", json={}).json()["session_id"]
    client.post(f"/api/v1/sessions/{session_id}/start")

    resp = client.post(
        f"/api/v1/sessions/{session_id}/coach/messages", json={"message": "hi"}
    )
    assert resp.status_code == 409


def test_end_session_then_end_again_returns_409(api_context) -> None:
    client = api_context.client
    session_id = client.post("/api/v1/sessions", json={}).json()["session_id"]
    client.post(f"/api/v1/sessions/{session_id}/start")

    first = client.post(f"/api/v1/sessions/{session_id}/end", json={"reason": "candidate_left"})
    assert first.status_code == 200
    assert first.json()["state"] == "TERMINATED"

    second = client.post(f"/api/v1/sessions/{session_id}/end")
    assert second.status_code == 409
