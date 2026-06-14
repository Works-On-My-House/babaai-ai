from app.agents.prompts import build_recipe_proposal_prompt


def test_build_recipe_proposal_prompt_includes_ingredients_and_limit():
    system, user = build_recipe_proposal_prompt(["Tomato", "Garlic", "Pasta"], limit=2)

    assert "BabaAI" in system
    assert "- Garlic" in user
    assert "- Pasta" in user
    assert "- Tomato" in user
    assert "exactly 2" in user
    assert '"name"' in user
    assert '"steps"' in user
    assert '"quantity"' in user
    assert '"unit"' in user
