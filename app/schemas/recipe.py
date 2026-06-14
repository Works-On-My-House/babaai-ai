from pydantic import BaseModel, Field


class AiProposalIngredient(BaseModel):
    product_name: str
    quantity: float | None = None
    unit: str | None = None


class AiRecipeProposal(BaseModel):
    name: str
    category: str = "AI Suggestion"
    preparation: str
    steps: list[str] = Field(default_factory=list)
    ingredients: list[AiProposalIngredient] = Field(default_factory=list)
    agent_id: str = "ollama-local"
    agent_label: str = "Ollama"
