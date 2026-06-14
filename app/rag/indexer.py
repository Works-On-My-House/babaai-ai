from __future__ import annotations

import hashlib
from uuid import UUID

from app.core.json_config import load_rag_config
from app.rag.qdrant_store import fetch_recipe_from_core, upsert_recipe_chunks


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def _stub_embedding(text: str, dimensions: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [((digest[i % len(digest)] / 255.0) * 2.0) - 1.0 for i in range(dimensions)]
    norm = sum(value * value for value in values) ** 0.5 or 1.0
    return [value / norm for value in values]


class RecipeIndexer:
    def __init__(self) -> None:
        self.config = load_rag_config()

    async def index_recipe(self, recipe_id: UUID) -> int:
        recipe = await fetch_recipe_from_core(recipe_id)
        if recipe is None:
            return 0
        text_parts = [
            recipe.get("name", ""),
            recipe.get("preparation", ""),
        ]
        for ingredient in recipe.get("ingredients", []):
            text_parts.append(
                f"{ingredient.get('product_name')} {ingredient.get('quantity')} {ingredient.get('unit')}"
            )
        full_text = "\n".join(part for part in text_parts if part)
        chunk_size = int(self.config.get("chunk_size", 512))
        overlap = int(self.config.get("chunk_overlap", 64))
        dimensions = int(self.config.get("embedding_dimensions", 1536))
        chunks = _chunk_text(full_text, chunk_size, overlap)
        payload = [
            (index, content, _stub_embedding(content, dimensions))
            for index, content in enumerate(chunks)
        ]
        return upsert_recipe_chunks(recipe_id, payload)
