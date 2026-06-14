from typing import Literal

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Agent definition loaded from agents.json."""

    id: str
    provider: Literal["ollama", "openai", "anthropic"]
    model: str
    tier: Literal["free", "paid"]
    roles: list[str] = Field(default_factory=list)
    api_key_env: str | None = None
    base_url_env: str | None = None
