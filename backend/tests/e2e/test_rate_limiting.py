"""Rate limiting is disabled by default in tests/e2e/conftest.py's fixture
so other tests can drive a full interview's worth of requests without
tripping it - this file is the one place it's deliberately re-enabled to
verify it actually works.
"""

from app.api.deps import get_gateway  # noqa: F401 - imported for clarity of what's overridden
from app.config import get_settings
from app.core.rate_limit import enforce_rate_limit, get_rate_limiter
from app.main import app


def test_answer_endpoint_rate_limits_after_threshold(api_context) -> None:
    del app.dependency_overrides[enforce_rate_limit]
    get_rate_limiter().reset()
    try:
        client = api_context.client
        headers = api_context.auth_headers()
        session_id = client.post("/api/v1/sessions", json={}, headers=headers).json()[
            "session_id"
        ]
        question = client.post(f"/api/v1/sessions/{session_id}/start").json()[
            "current_question"
        ]
        limit = get_settings().rate_limit_per_minute

        for _ in range(limit):
            response = client.post(
                f"/api/v1/sessions/{session_id}/answer",
                json={"question_id": question["question_id"], "transcript_text": "an answer"},
            )
            assert response.status_code != 429

        over_limit_response = client.post(
            f"/api/v1/sessions/{session_id}/answer",
            json={"question_id": question["question_id"], "transcript_text": "an answer"},
        )
        assert over_limit_response.status_code == 429
        assert over_limit_response.json()["error_code"] == "rate_limited"
    finally:
        get_rate_limiter().reset()
        app.dependency_overrides[enforce_rate_limit] = lambda: None


def test_rate_limit_is_scoped_per_session(api_context) -> None:
    del app.dependency_overrides[enforce_rate_limit]
    get_rate_limiter().reset()
    try:
        client = api_context.client
        limit = get_settings().rate_limit_per_minute
        headers = api_context.auth_headers()

        session_a = client.post("/api/v1/sessions", json={}, headers=headers).json()[
            "session_id"
        ]
        question_a = client.post(f"/api/v1/sessions/{session_a}/start").json()[
            "current_question"
        ]
        for _ in range(limit):
            client.post(
                f"/api/v1/sessions/{session_a}/answer",
                json={"question_id": question_a["question_id"], "transcript_text": "answer"},
            )

        # A different session (even from the same test client / IP) should
        # not be affected by session_a's exhausted quota.
        session_b = client.post("/api/v1/sessions", json={}, headers=headers).json()[
            "session_id"
        ]
        question_b = client.post(f"/api/v1/sessions/{session_b}/start").json()[
            "current_question"
        ]
        response = client.post(
            f"/api/v1/sessions/{session_b}/answer",
            json={"question_id": question_b["question_id"], "transcript_text": "answer"},
        )
        assert response.status_code != 429
    finally:
        get_rate_limiter().reset()
        app.dependency_overrides[enforce_rate_limit] = lambda: None
