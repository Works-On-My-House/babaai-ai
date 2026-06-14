import logging
import os
from collections.abc import Awaitable, Callable

import httpx

from app.agents.base import AgentConfig
from app.core.config import get_settings

logger = logging.getLogger(__name__)

GenerateHandler = Callable[[str, str | None], Awaitable[str | None]]


class LLMClient:
    """Single LLM client — dispatches to the configured provider backend."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.settings = get_settings()
        self._handlers: dict[str, GenerateHandler] = {
            "ollama": self._generate_ollama,
            "openai": self._generate_openai,
            "anthropic": self._generate_anthropic,
        }

    async def generate(self, prompt: str, *, system: str | None = None) -> str | None:
        handler = self._handlers.get(self.config.provider)
        if handler is None:
            logger.warning("Unsupported provider: %s", self.config.provider)
            return None
        return await handler(prompt, system)

    def _build_messages(self, prompt: str, system: str | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def _generate_ollama(self, prompt: str, system: str | None) -> str | None:
        base_url = self.settings.ollama_base_url.rstrip("/")
        model = self.config.model or self.settings.ollama_model

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": self._build_messages(prompt, system),
                        "stream": False,
                    },
                )
                response.raise_for_status()
                content = response.json().get("message", {}).get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        except httpx.HTTPError as exc:
            logger.warning("Ollama request failed for agent %s: %s", self.config.id, exc)
        return None

    async def _generate_openai(self, prompt: str, system: str | None) -> str | None:
        """TODO: OpenAI chat completions."""
        api_key = self._resolve_secret(self.config.api_key_env)
        if not api_key:
            return None
        _ = (prompt, system, api_key)
        return None

    async def _generate_anthropic(self, prompt: str, system: str | None) -> str | None:
        """TODO: Anthropic messages API."""
        api_key = self._resolve_secret(self.config.api_key_env)
        if not api_key:
            return None
        _ = (prompt, system, api_key)
        return None

    def _resolve_secret(self, env_name: str | None) -> str | None:
        if not env_name:
            return None
        return os.getenv(env_name)
