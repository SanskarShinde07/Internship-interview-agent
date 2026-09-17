from unittest.mock import MagicMock, patch

import pytest

from app.ai.gateway import GeminiAIGateway, StubAIGateway, get_default_gateway
from app.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_factory_returns_stub_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    gateway = get_default_gateway()
    assert isinstance(gateway, StubAIGateway)


def test_factory_returns_gemini_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    with (
        patch("app.ai.gateway.genai.GenerativeModel", side_effect=lambda *a, **k: MagicMock()),
        patch("app.ai.gateway.genai.configure"),
    ):
        gateway = get_default_gateway()
    assert isinstance(gateway, GeminiAIGateway)
