from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ai_health(client: TestClient) -> None:
    response = client.get("/api/v1/ai/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "babaai-ai"


def test_proposals_requires_service_token(client: TestClient) -> None:
    response = client.post("/api/v1/ai/proposals", json={"pantry_names": ["egg"], "limit": 1})
    assert response.status_code == 401


def test_proposals_with_valid_token_and_empty_pantry(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ai/proposals",
        headers={"X-Service-Token": "test-ai-token"},
        json={"pantry_names": [], "limit": 3},
    )
    assert response.status_code == 200
    # Empty pantry → no proposals and no error (nothing to suggest, not a failure).
    assert response.json() == {"proposals": [], "error": None}


def test_reindex_requires_service_token(client: TestClient) -> None:
    response = client.post("/api/v1/ai/reindex", json={"recipe_id": str(uuid4())})
    assert response.status_code == 401


def test_rag_qa_requires_bearer_token(client: TestClient) -> None:
    response = client.post("/api/v1/ai/rag/qa", json={"question": "What is BabaAI?"})
    assert response.status_code == 401
