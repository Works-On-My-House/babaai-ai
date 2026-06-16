from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.chains.rag_qa import answer_with_rag
from app.agents.chains.recipe_proposal import propose_recipes
from app.api.deps import (
    RoutingDecision,
    get_current_user_id,
    require_service_token,
    route_request,
)
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
    # Set when there are no proposals AND there's a user-facing reason (e.g. the model failed).
    # The frontend shows this so a failure isn't silently an empty section.
    error: str | None = None


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
    logger.info(
        "ai_proposals: ollama_enabled=%s pantry_names=%d limit=%d",
        settings.ollama_enabled,
        len(body.pantry_names),
        body.limit,
    )
    if not settings.ollama_enabled:
        logger.warning("ai_proposals: returning empty — Ollama is disabled")
        return ProposalResponse(error="AI suggestions are currently disabled.")
    if not body.pantry_names:
        logger.info("ai_proposals: no pantry ingredients provided — nothing to suggest")
        return ProposalResponse()
    raw = await propose_recipes(body.pantry_names, limit=body.limit)
    logger.info("ai_proposals: Ollama produced %d proposal(s)", len(raw))
    if not raw:
        logger.warning("ai_proposals: returning empty — Ollama produced no usable proposals")
        return ProposalResponse(
            error="AI suggestions are temporarily unavailable. Please try again."
        )
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


class SuggestionRequest(BaseModel):
    prompt: str = Field(min_length=1)


@router.post("/suggestions", response_model=RoutingDecision)
async def ai_suggestions(
    body: SuggestionRequest,
    decision: RoutingDecision = Depends(route_request),
) -> RoutingDecision:
    """User-facing AI entrypoint (FE → gateway → ai, direct).

    Skeleton: any authenticated user is admitted; ``route_request`` resolves the tier
    (premium vs free Ollama) and enforces the premium daily quota. The streaming LLM
    call against ``decision.agent_id`` is out of scope here (ClickUp 869dqh96c).
    """
    _ = body
    return decision


@router.get("/health")
def ai_health() -> dict[str, str]:
    return {"status": "ok", "service": "babaai-ai"}
