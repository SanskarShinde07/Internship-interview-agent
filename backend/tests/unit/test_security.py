import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import get_settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_reset_token,
    decode_token,
    hash_password,
    verify_password,
)


@pytest.fixture(autouse=True)
def _clear_settings_cache(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_hash_password_is_not_plaintext_and_verifies() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("correct horse battery staple")
    assert not verify_password("wrong password", hashed)


def test_verify_password_rejects_malformed_hash() -> None:
    assert not verify_password("anything", "not-a-real-bcrypt-hash")


def test_access_token_round_trips_to_same_user_id() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    assert decode_token(token, expected_purpose="access") == user_id


def test_reset_token_round_trips_to_same_user_id() -> None:
    user_id = uuid.uuid4()
    token = create_reset_token(user_id)
    assert decode_token(token, expected_purpose="reset") == user_id


def test_access_token_rejected_when_expecting_reset_purpose() -> None:
    token = create_access_token(uuid.uuid4())
    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_purpose="reset")


def test_reset_token_rejected_when_expecting_access_purpose() -> None:
    token = create_reset_token(uuid.uuid4())
    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_purpose="access")


def test_garbage_token_is_rejected() -> None:
    with pytest.raises(InvalidTokenError):
        decode_token("not.a.jwt", expected_purpose="access")


def test_token_signed_with_wrong_secret_is_rejected() -> None:
    forged = jwt.encode(
        {"sub": str(uuid.uuid4()), "purpose": "access"}, "a-different-secret", algorithm="HS256"
    )
    with pytest.raises(InvalidTokenError):
        decode_token(forged, expected_purpose="access")


def test_expired_token_is_rejected() -> None:
    settings = get_settings()
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "purpose": "access",
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }
    expired_token = jwt.encode(
        expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    with pytest.raises(InvalidTokenError):
        decode_token(expired_token, expected_purpose="access")
