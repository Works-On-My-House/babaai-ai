from app.agents.client import LLMClient
from app.agents.registry import AgentRegistry


class AgentRouter:
    """Role-based agent selection with ordered fallback."""

    def __init__(self, registry: AgentRegistry | None = None) -> None:
        self.registry = registry or AgentRegistry()

    async def route(
        self,
        task: str,
        prompt: str,
        *,
        system: str | None = None,
        json_format: bool = False,
    ) -> str | None:
        for agent_id in self.registry.routing_chain(task):
            if not self.registry.is_available(agent_id):
                continue
            agent = self.registry.get(agent_id)
            if agent is None:
                continue
            result = await LLMClient(agent).generate(
                prompt, system=system, json_format=json_format
            )
            if result:
                return result
        return None
