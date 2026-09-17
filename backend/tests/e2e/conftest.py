from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ai.gateway import StubAIGateway
from app.api.deps import get_db, get_gateway
from app.core.rate_limit import enforce_auth_rate_limit, enforce_rate_limit
from app.db.models import Base
from app.main import app
from app.question_bank.loader import seed_question_bank


@dataclass
class ApiTestContext:
    client: TestClient
    session_factory: sessionmaker[Session]

    def auth_headers(self, email: str = "test-candidate@example.com") -> dict[str, str]:
        """Registers a fresh account and returns an Authorization header for
        it - POST /sessions requires a signed-in user, so any test driving
        the interview flow through the API needs one."""
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "test-password-123"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


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
    # These tests drive a full interview's worth of requests - and, now
    # that starting a session requires an account, at least one register()
    # call each - back-to-back, which isn't what either rate limiter is
    # meant to catch; both get their own dedicated tests in
    # test_rate_limiting.py.
    app.dependency_overrides[enforce_rate_limit] = lambda: None
    app.dependency_overrides[enforce_auth_rate_limit] = lambda: None

    with TestClient(app) as test_client:
        yield ApiTestContext(client=test_client, session_factory=test_session_factory)

    app.dependency_overrides.clear()
