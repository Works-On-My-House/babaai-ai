import asyncio
import json

from app.agents.chains.recipe_proposal import _extract_json_array, propose_recipes


def test_extract_json_array_from_markdown_block():
    text = """Here are ideas:
```json
[{"name":"Egg Scramble","steps":["Beat and cook."],"ingredients":[{"product_name":"Eggs","quantity":3,"unit":"pcs"}]}]
```"""
    items = _extract_json_array(text)
    assert len(items) == 1
    assert items[0]["name"] == "Egg Scramble"


def test_extract_json_array_from_plain_json():
    text = json.dumps(
        [{"name": "Pasta Bowl", "steps": ["Boil pasta."], "ingredients": ["Pasta"]}]
    )
    items = _extract_json_array(text)
    assert items[0]["name"] == "Pasta Bowl"


def test_propose_recipes_returns_structured_proposals(monkeypatch):
    class FakeRouter:
        async def route(self, task, prompt, *, system=None):
            _ = (task, prompt, system)
            return json.dumps(
                [
                    {
                        "name": "Tomato Garlic Pasta",
                        "category": "Pasta",
                        "ingredients": [
                            {"product_name": "Tomato", "quantity": 3, "unit": "pcs"},
                            {"product_name": "Garlic", "quantity": 2, "unit": "cloves"},
                            {"product_name": "Pasta", "quantity": 200, "unit": "g"},
                        ],
                        "steps": [
                            "Boil the pasta for 9 minutes.",
                            "Saute garlic, add tomatoes, toss with pasta.",
                        ],
                    }
                ]
            )

    monkeypatch.setattr("app.agents.chains.recipe_proposal.AgentRouter", FakeRouter)

    proposals = asyncio.run(propose_recipes(["Tomato", "Garlic", "Pasta"], limit=1))
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.name == "Tomato Garlic Pasta"
    assert proposal.category == "Pasta"
    assert proposal.agent_label == "Ollama"

    names = {item.product_name for item in proposal.ingredients}
    assert {"Tomato", "Garlic", "Pasta"} <= names
    pasta = next(item for item in proposal.ingredients if item.product_name == "Pasta")
    assert pasta.quantity == 200
    assert pasta.unit == "g"

    assert len(proposal.steps) == 2
    # preparation is derived from numbered steps when not explicitly provided
    assert "1." in proposal.preparation


def test_propose_recipes_accepts_plain_string_ingredients(monkeypatch):
    class FakeRouter:
        async def route(self, task, prompt, *, system=None):
            _ = (task, prompt, system)
            return json.dumps(
                [
                    {
                        "name": "Simple Toast",
                        "preparation": "Toast the bread.",
                        "ingredients": ["Bread"],
                    }
                ]
            )

    monkeypatch.setattr("app.agents.chains.recipe_proposal.AgentRouter", FakeRouter)

    proposals = asyncio.run(propose_recipes(["Bread"], limit=1))
    assert proposals[0].ingredients[0].product_name == "Bread"
    assert proposals[0].steps == ["Toast the bread."]
