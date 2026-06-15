from __future__ import annotations

import logging
from uuid import UUID

import httpx
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from app.core.config import get_settings
from app.core.json_config import load_rag_config

logger = logging.getLogger(__name__)


def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection() -> None:
    settings = get_settings()
    rag = load_rag_config()
    dimensions = int(rag.get("embedding_dimensions", 1536))
    client = get_qdrant_client()
    collections = {item.name for item in client.get_collections().collections}
    if settings.qdrant_collection not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection %s", settings.qdrant_collection)


def upsert_recipe_chunks(recipe_id: UUID, chunks: list[tuple[int, str, list[float]]]) -> int:
    settings = get_settings()
    client = get_qdrant_client()
    points = [
        PointStruct(
            id=f"{recipe_id}-{index}",
            vector=embedding,
            payload={"recipe_id": str(recipe_id), "chunk_index": index, "content": content},
        )
        for index, content, embedding in chunks
    ]
    if not points:
        client.delete(
            collection_name=settings.qdrant_collection,
            points_selector={
                "filter": {
                    "must": [{"key": "recipe_id", "match": {"value": str(recipe_id)}}],
                },
            },
        )
        return 0
    client.upsert(collection_name=settings.qdrant_collection, points=points)
    return len(points)


def search_similar(query_vector: list[float], top_k: int = 5) -> list[dict]:
    settings = get_settings()
    client = get_qdrant_client()
    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=top_k,
    )
    return [
        {
            "recipe_id": hit.payload.get("recipe_id"),
            "content": hit.payload.get("content"),
            "score": hit.score,
        }
        for hit in results
    ]


async def fetch_recipe_from_core(recipe_id: UUID) -> dict | None:
    settings = get_settings()
    url = f"{settings.core_base_url}/api/v1/recipes/{recipe_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


async def ingest_recipe_to_core(payload: dict) -> dict:
    settings = get_settings()
    url = f"{settings.core_base_url}/api/v1/internal/recipes/ingest"
    headers = {"X-Service-Token": settings.core_service_token}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
