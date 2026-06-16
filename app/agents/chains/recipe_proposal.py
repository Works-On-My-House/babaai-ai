import json
import logging
import re

from app.agents.prompts import build_recipe_proposal_prompt
from app.agents.router import AgentRouter
from app.schemas.recipe import AiProposalIngredient, AiRecipeProposal

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _coerce_quantity(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:[.,]\d+)?", value)
        if match:
            try:
                return float(match.group(0).replace(",", "."))
            except ValueError:
                return None
    return None


def _parse_ai_ingredients(raw: object) -> list[AiProposalIngredient]:
    """Accept either structured objects or plain strings from the model."""
    if not isinstance(raw, list):
        return []

    ingredients: list[AiProposalIngredient] = []
    for item in raw:
        if isinstance(item, dict):
            name = str(item.get("product_name") or item.get("name") or "").strip()
            if not name:
                continue
            unit_value = item.get("unit")
            ingredients.append(
                AiProposalIngredient(
                    product_name=name,
                    quantity=_coerce_quantity(item.get("quantity")),
                    unit=str(unit_value).strip() if unit_value else None,
                )
            )
        elif isinstance(item, str) and item.strip():
            ingredients.append(AiProposalIngredient(product_name=item.strip()))
    return ingredients


def _parse_steps(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [str(step).strip() for step in raw if str(step).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def _slice_outer(text: str, open_ch: str, close_ch: str) -> str | None:
    start = text.find(open_ch)
    end = text.rfind(close_ch)
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _load_json(text: str) -> object | None:
    """Parse the whole payload (clean JSON), else an outermost ``[...]`` or ``{...}`` slice."""
    for candidate in (text, _slice_outer(text, "[", "]"), _slice_outer(text, "{", "}")):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _extract_json_array(text: str) -> list[dict]:
    stripped = text.strip()
    block = _JSON_BLOCK_RE.search(stripped)
    if block:
        stripped = block.group(1).strip()

    parsed = _load_json(stripped)
    if parsed is None:
        logger.warning("Failed to parse Ollama recipe JSON")
        return []

    # Accept a top-level array, a single recipe object, or a wrapper like {"recipes": [...]}.
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        if "name" in parsed:
            return [parsed]
        for value in parsed.values():
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


async def propose_recipes(
    ingredient_names: list[str],
    *,
    limit: int = 3,
    agent_id: str = "ollama-local",
) -> list[AiRecipeProposal]:
    """Ask Ollama to propose creative recipes from pantry ingredients."""
    if not ingredient_names:
        return []

    router = AgentRouter()
    system, prompt = build_recipe_proposal_prompt(ingredient_names, limit=limit)
    raw = await router.route("recipe_proposal", prompt, system=system, json_format=True)
    if not raw:
        return []

    proposals: list[AiRecipeProposal] = []
    for item in _extract_json_array(raw)[:limit]:
        name = str(item.get("name", "")).strip()
        category = str(item.get("category", "") or "AI Suggestion").strip() or "AI Suggestion"
        steps = _parse_steps(item.get("steps"))
        preparation = str(item.get("preparation", "")).strip()

        if not preparation and steps:
            preparation = "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1))
        if not steps and preparation:
            steps = [preparation]

        ingredients_list = _parse_ai_ingredients(item.get("ingredients", []))
        if not name or not preparation:
            continue

        proposals.append(
            AiRecipeProposal(
                name=name,
                category=category,
                preparation=preparation,
                steps=steps,
                ingredients=ingredients_list,
                agent_id=agent_id,
                agent_label="Ollama",
            )
        )
    return proposals
