import os

from app.agents.base import AgentConfig
from app.core.config import get_settings
from app.core.json_config import load_agents_config


class AgentRegistry:
    """Loads and validates agent definitions from agents.json."""

    def __init__(self) -> None:
        self._config = load_agents_config()
        self._agents: dict[str, AgentConfig] = {}
        self._load()

    def _load(self) -> None:
        for entry in self._config.get("agents", []):
            agent = AgentConfig.model_validate(entry)
            self._agents[agent.id] = agent

    def get(self, agent_id: str) -> AgentConfig | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[AgentConfig]:
        return list(self._agents.values())

    def is_available(self, agent_id: str) -> bool:
        agent = self.get(agent_id)
        if agent is None:
            return False
        if agent.provider == "ollama":
            settings = get_settings()
            return settings.ollama_enabled and bool(settings.ollama_base_url)
        if not get_settings().agents_enabled:
            return False
        if agent.api_key_env and not os.getenv(agent.api_key_env):
            return False
        return True

    def routing_chain(self, task: str) -> list[str]:
        """Return ordered agent ids for a routing task key."""
        routing = self._config.get("routing", {})
        return list(routing.get(task, []))
