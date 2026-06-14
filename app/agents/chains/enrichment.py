from app.agents.prompts import build_enrichment_prompt
from app.agents.router import AgentRouter


async def enrich_suggestion(recipe_name: str, preparation: str) -> str | None:
    """Post-process matcher suggestions with LLM enrichment."""
    router = AgentRouter()
    system, prompt = build_enrichment_prompt(recipe_name, preparation)
    return await router.route("suggestion_enrichment", prompt, system=system)
