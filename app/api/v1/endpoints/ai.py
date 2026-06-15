from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.chains.rag_qa import answer_with_rag
from app.agents.chains.recipe_proposal import propose_recipes
from app.api.deps import get_current_user_id, require_service_token
from app.core.config import get_settings
from app.rag.indexer import RecipeIndexer
from app.rag.schemas import RagQuestionRequest, RagQuestionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


class ProposalRequest(BaseModel):
    pantry_names: list[str] = Field(default_factory=list)
    limit: int = Field(default=3, ge=1, le=10)


class ProposalIngredient(BaseModel):
    product_name: str
    quantity: float | None = None
    unit: str | None = None


class AiRecipeProposal(BaseModel):
    name: str
    category: str = "AI Suggestion"
    preparation: str
    steps: list[str] = Field(default_factory=list)
    ingredients: list[ProposalIngredient] = Field(default_factory=list)
    agent_id: str = "ollama-local"
    agent_label: str = "Ollama"


class ProposalResponse(BaseModel):
    proposals: list[AiRecipeProposal] = Field(default_factory=list)


class ReindexRequest(BaseModel):
    recipe_id: UUID


class ReindexResponse(BaseModel):
    indexed_chunks: int


@router.post("/proposals", response_model=ProposalResponse)
async def ai_proposals(
    body: ProposalRequest,
    _: None = Depends(require_service_token),
) -> ProposalResponse:
    settings = get_settings()
    if not settings.ollama_enabled or not body.pantry_names:
        return ProposalResponse()
    raw = await propose_recipes(body.pantry_names, limit=body.limit)
    proposals = [
        AiRecipeProposal(
            name=item.name,
            category=item.category,
            preparation=item.preparation,
            steps=item.steps,
            ingredients=[
                ProposalIngredient(
                    product_name=ing.product_name,
                    quantity=ing.quantity,
                    unit=ing.unit,
                )
                for ing in item.ingredients
            ],
            agent_id=item.agent_id,
            agent_label=item.agent_label,
        )
        for item in raw
    ]
    return ProposalResponse(proposals=proposals)


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_recipe(
    body: ReindexRequest,
    _: None = Depends(require_service_token),
) -> ReindexResponse:
    indexer = RecipeIndexer()
    count = await indexer.index_recipe(body.recipe_id)
    return ReindexResponse(indexed_chunks=count)


@router.post("/rag/qa", response_model=RagQuestionResponse)
async def rag_qa(
    body: RagQuestionRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> RagQuestionResponse:
    _ = user_id
    return await answer_with_rag(body.question)


@router.get("/health")
def ai_health() -> dict[str, str]:
    return {"status": "ok", "service": "babaai-ai"}
