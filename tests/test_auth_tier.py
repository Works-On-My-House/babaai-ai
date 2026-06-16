from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import Principal, current_principal
from app.core import quota
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _override_principal(permissions: frozenset[str]) -> Principal:
    principal = Principal(user_id=uuid4(), permissions=permissions)
    app.dependency_overrides[current_principal] = lambda: principal
    return principal


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_suggestions_requires_bearer_token(client: TestClient) -> None:
    response = client.post("/api/v1/ai/suggestions", json={"prompt": "hi"})
    assert response.status_code == 401


def test_suggestions_free_tier_without_pro_permission(client: TestClient) -> None:
    _override_principal(frozenset())
    response = client.post("/api/v1/ai/suggestions", json={"prompt": "hi"})
    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "free"
    assert body["agent_id"] == "ollama-local"
    assert body["quota_remaining"] is None


def test_suggestions_premium_tier_with_pro_permission(client: TestClient) -> None:
    _override_principal(frozenset({"AI_PRO_SUGGESTIONS"}))
    response = client.post("/api/v1/ai/suggestions", json={"prompt": "hi"})
    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "premium"
    assert body["agent_id"] == "openai-primary"
    # Fresh in-memory counter → usage 0, full quota remaining.
    assert body["quota_remaining"] == 100_000


def test_suggestions_premium_quota_exceeded_returns_429(client: TestClient, monkeypatch) -> None:
    _override_principal(frozenset({"AI_PRO_SUGGESTIONS"}))

    async def _fake_usage(_user_id):
        return 100_000

    monkeypatch.setattr(quota, "get_usage", _fake_usage)
    response = client.post("/api/v1/ai/suggestions", json={"prompt": "hi"})
    assert response.status_code == 429


def test_usage_counter_round_trip() -> None:
    async def scenario() -> None:
        user_id = uuid4()
        assert await quota.get_usage(user_id) == 0
        assert await quota.record_tokens(user_id, 120) == 120
        assert await quota.record_tokens(user_id, 30) == 150
        assert await quota.get_usage(user_id) == 150

    asyncio.run(scenario())
