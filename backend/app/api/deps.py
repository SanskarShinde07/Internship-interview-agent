"""FastAPI dependencies (docs/BLUEPRINT.md §4, §17): the DB session and
AI Gateway are injected here so tests can override them (a seeded test
DB, a StubAIGateway) without touching route code.
"""

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.ai.gateway import AIGateway, get_default_gateway
from app.core.auth_errors import InvalidCredentialsError
from app.core.security import InvalidTokenError, decode_token
from app.db.models import User
from app.db.session import get_db as _get_db

_bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


@lru_cache
def _cached_gateway() -> AIGateway:
    return get_default_gateway()


def get_gateway() -> AIGateway:
    return _cached_gateway()


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Returns the signed-in user if a valid access token was sent, else
    None. Used where auth is a nice-to-have (e.g. linking a new interview
    session to whoever's logged in) rather than required."""
    if credentials is None:
        return None
    try:
        user_id = decode_token(credentials.credentials, expected_purpose="access")
    except InvalidTokenError:
        return None
    return db.get(User, user_id)


def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    """Same as get_current_user_optional but raises when there's no valid
    session - for routes that require the caller to be signed in."""
    if user is None:
        raise InvalidCredentialsError("Sign in to access this.")
    return user
