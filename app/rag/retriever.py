from __future__ import annotations

import hashlib

from app.core.json_config import load_rag_config
from app.rag.qdrant_store import search_similar
from app.rag.schemas import RetrievedChunk


class RecipeRetriever:
    def __init__(self) -> None:
        self.config = load_rag_config()

    def _embed_query(self, query: str) -> list[float]:
        dimensions = int(self.config.get("embedding_dimensions", 1536))
        digest = hashlib.sha256(query.encode("utf-8")).digest()
        values = [((digest[i % len(digest)] / 255.0) * 2.0) - 1.0 for i in range(dimensions)]
        norm = sum(value * value for value in values) ** 0.5 or 1.0
        return [value / norm for value in values]

    def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
        limit = top_k or int(self.config.get("top_k", 5))
        hits = search_similar(self._embed_query(query), top_k=limit)
        chunks: list[RetrievedChunk] = []
        for hit in hits:
            recipe_id = hit.get("recipe_id")
            content = hit.get("content")
            score = float(hit.get("score") or 0.0)
            if not recipe_id or not content:
                continue
            chunks.append(
                RetrievedChunk(
                    recipe_id=str(recipe_id),
                    content=str(content),
                    score=min(max(score, 0.0), 1.0),
                )
            )
        return chunks
