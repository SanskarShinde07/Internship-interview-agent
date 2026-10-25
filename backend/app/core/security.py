"""Password hashing and JWT issuance/verification for the optional auth
layer (docs/BLUEPRINT.md §21 follow-up). Kept separate from app.core.email
so the two concerns - "is this credential valid" and "how do we notify the
user" - can be tested and reasoned about independently.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
import jwt

from app.config import get_settings

TokenPurpose = Literal["access", "reset"]


class InvalidTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash (shouldn't happen against our own data) - treat as
        # a failed check rather than a 500.
        return False


def _create_token(user_id: uuid.UUID, purpose: TokenPurpose, expire_minutes: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "purpose": purpose,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    return _create_token(user_id, "access", settings.jwt_expire_minutes)


def create_reset_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    return _create_token(user_id, "reset", settings.password_reset_token_expire_minutes)


def decode_token(token: str, *, expected_purpose: TokenPurpose) -> uuid.UUID:
    """Returns the user id encoded in the token, or raises InvalidTokenError
    for anything wrong with it - expired, wrong purpose, bad signature,
    malformed subject. Callers never need to distinguish why; an invalid
    token is an invalid token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("invalid or expired token") from exc

    if payload.get("purpose") != expected_purpose:
        raise InvalidTokenError("token is not valid for this operation")

    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("invalid token subject") from exc
