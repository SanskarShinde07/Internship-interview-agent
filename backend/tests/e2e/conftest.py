from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ai.gateway import StubAIGateway
from app.api.deps import get_db, get_gateway
from app.core.rate_limit import enforce_rate_limit
from app.db.models import Base
from app.main import app
from app.question_bank.loader import seed_question_bank


@dataclass
class ApiTestContext:
    client: TestClient
    session_factory: sessionmaker[Session]


@pytest.fixture
def api_context(tmp_path) -> Generator[ApiTestContext, None, None]:
    db_path = tmp_path / "api_test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    seed_db = test_session_factory()
    seed_question_bank(seed_db)
    seed_db.close()

    def override_get_db() -> Generator[Session, None, None]:
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    stub_gateway = StubAIGateway()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_gateway] = lambda: stub_gateway
    # These tests drive a full interview's worth of requests back-to-back,
    # which isn't what the rate limiter is meant to catch - rate limiting
    # itself gets its own dedicated test in test_rate_limiting.py.
    app.dependency_overrides[enforce_rate_limit] = lambda: None

    with TestClient(app) as test_client:
        yield ApiTestContext(client=test_client, session_factory=test_session_factory)

    app.dependency_overrides.clear()
