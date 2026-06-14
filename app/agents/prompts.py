from app.core.json_config import load_prompts_config


def _format_ingredient_list(names: list[str]) -> str:
    unique = sorted({name.strip() for name in names if name.strip()})
    if not unique:
        return "(none)"
    return "\n".join(f"- {name}" for name in unique)


def build_recipe_proposal_prompt(
    ingredient_names: list[str],
    *,
    limit: int | None = None,
) -> tuple[str, str]:
    """Return (system, user) prompts for pantry-based recipe suggestions."""
    config = load_prompts_config()["recipe_proposal"]
    resolved_limit = limit if limit is not None else int(config.get("default_limit", 3))
    user = config["user_template"].format(
        ingredients=_format_ingredient_list(ingredient_names),
        limit=resolved_limit,
    )
    return config["system"], user


def build_enrichment_prompt(recipe_name: str, preparation: str) -> tuple[str, str]:
    """Return (system, user) prompts for enriching a catalog suggestion."""
    config = load_prompts_config()["suggestion_enrichment"]
    user = config["user_template"].format(
        recipe_name=recipe_name,
        preparation=preparation,
    )
    return config["system"], user
