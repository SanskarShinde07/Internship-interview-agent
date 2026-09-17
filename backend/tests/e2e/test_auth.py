"""Integration tests for the auth flow (docs/BLUEPRINT.md §21 follow-up):
register, login, /me, forgot/reset password, and that a signed-in
candidate's interview sessions show up in their own history."""

import uuid

import pytest

from app.config import get_settings
from app.core.rate_limit import get_rate_limiter
from app.core.security import create_reset_token
from tests.e2e.conftest import ApiTestContext


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter():
    # This file's own dedicated concern is the auth flow, not rate
    # limiting (that has its own tests in test_rate_limiting.py) - and
    # several tests here register/log in more than once, which would
    # otherwise trip the auth endpoints' tighter per-IP limit.
    get_rate_limiter().reset()
    yield
    get_rate_limiter().reset()


def _register(client, email="candidate@example.com", password="password123", display_name=None):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )


def test_register_returns_token_and_user(api_context: ApiTestContext) -> None:
    response = _register(api_context.client)
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "candidate@example.com"


def test_register_duplicate_email_is_rejected(api_context: ApiTestContext) -> None:
    _register(api_context.client)
    response = _register(api_context.client)
    assert response.status_code == 409
    assert response.json()["error_code"] == "email_already_registered"


def test_register_email_is_case_insensitive_for_duplicates(api_context: ApiTestContext) -> None:
    _register(api_context.client, email="Candidate@Example.com")
    response = _register(api_context.client, email="candidate@example.com")
    assert response.status_code == 409


def test_login_with_correct_credentials_succeeds(api_context: ApiTestContext) -> None:
    _register(api_context.client)
    response = api_context.client.post(
        "/api/v1/auth/login",
        json={"email": "candidate@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_with_wrong_password_is_rejected(api_context: ApiTestContext) -> None:
    _register(api_context.client)
    response = api_context.client.post(
        "/api/v1/auth/login",
        json={"email": "candidate@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "invalid_credentials"


def test_login_with_unknown_email_is_rejected(api_context: ApiTestContext) -> None:
    response = api_context.client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever123"},
    )
    assert response.status_code == 401


def test_me_requires_a_token(api_context: ApiTestContext) -> None:
    response = api_context.client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_the_authenticated_user(api_context: ApiTestContext) -> None:
    register_response = _register(api_context.client, display_name="Ada")
    token = register_response.json()["access_token"]

    response = api_context.client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "candidate@example.com"
    assert body["display_name"] == "Ada"


def test_me_rejects_a_garbage_token(api_context: ApiTestContext) -> None:
    response = api_context.client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_forgot_password_gives_same_response_for_known_and_unknown_email(
    api_context: ApiTestContext,
) -> None:
    _register(api_context.client)
    known = api_context.client.post(
        "/api/v1/auth/forgot-password", json={"email": "candidate@example.com"}
    )
    unknown = api_context.client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json()


def test_reset_password_with_valid_token_changes_the_password(
    api_context: ApiTestContext,
) -> None:
    register_response = _register(api_context.client)
    user_id = uuid.UUID(register_response.json()["user"]["id"])

    reset_token = create_reset_token(user_id)
    reset_response = api_context.client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "brand-new-password"},
    )
    assert reset_response.status_code == 200

    old_login = api_context.client.post(
        "/api/v1/auth/login",
        json={"email": "candidate@example.com", "password": "password123"},
    )
    assert old_login.status_code == 401

    new_login = api_context.client.post(
        "/api/v1/auth/login",
        json={"email": "candidate@example.com", "password": "brand-new-password"},
    )
    assert new_login.status_code == 200


def test_reset_password_rejects_an_access_token(api_context: ApiTestContext) -> None:
    register_response = _register(api_context.client)
    access_token = register_response.json()["access_token"]

    response = api_context.client.post(
        "/api/v1/auth/reset-password",
        json={"token": access_token, "new_password": "brand-new-password"},
    )
    assert response.status_code == 401


def test_session_created_while_authenticated_appears_in_my_interviews(
    api_context: ApiTestContext,
) -> None:
    register_response = _register(api_context.client)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_response = api_context.client.post("/api/v1/sessions", headers=headers, json={})
    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    history_response = api_context.client.get("/api/v1/auth/me/interviews", headers=headers)
    assert history_response.status_code == 200
    session_ids = [item["session_id"] for item in history_response.json()["sessions"]]
    assert session_id in session_ids


def test_creating_a_session_without_being_signed_in_is_rejected(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post("/api/v1/sessions", json={})
    assert response.status_code == 401


def test_creating_a_session_with_a_garbage_token_is_rejected(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post(
        "/api/v1/sessions",
        json={},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


def test_two_users_only_see_their_own_sessions(api_context: ApiTestContext) -> None:
    token_a = _register(api_context.client, email="a@example.com").json()["access_token"]
    token_b = _register(api_context.client, email="b@example.com").json()["access_token"]

    api_context.client.post(
        "/api/v1/sessions", headers={"Authorization": f"Bearer {token_a}"}, json={}
    )

    history_b = api_context.client.get(
        "/api/v1/auth/me/interviews", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert history_b.json()["sessions"] == []

    history_a = api_context.client.get(
        "/api/v1/auth/me/interviews", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert len(history_a.json()["sessions"]) == 1
