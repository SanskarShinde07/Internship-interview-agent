"""FastAPI dependencies (docs/BLUEPRINT.md §4, §17): the DB session and
AI Gateway are injected here so tests can override them (a seeded test
DB, a StubAIGateway) without touching route code.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session

from app.ai.gateway import AIGateway, get_default_gateway
from app.db.session import get_db as _get_db


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


@lru_cache
def _cached_gateway() -> AIGateway:
    return get_default_gateway()


def get_gateway() -> AIGateway:
    return _cached_gateway()
