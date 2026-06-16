import logging
import os
from collections.abc import Awaitable, Callable

import httpx

from app.agents.base import AgentConfig
from app.core.config import get_settings

logger = logging.getLogger(__name__)

GenerateHandler = Callable[[str, str | None, bool], Awaitable[str | None]]


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

    async def generate(
        self, prompt: str, *, system: str | None = None, json_format: bool = False
    ) -> str | None:
        handler = self._handlers.get(self.config.provider)
        if handler is None:
            logger.warning("Unsupported provider: %s", self.config.provider)
            return None
        return await handler(prompt, system, json_format)

    def _build_messages(self, prompt: str, system: str | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def _generate_ollama(
        self, prompt: str, system: str | None, json_format: bool = False
    ) -> str | None:
        base_url = self.settings.ollama_base_url.rstrip("/")
        model = self.config.model or self.settings.ollama_model

        payload: dict = {
            "model": model,
            "messages": self._build_messages(prompt, system),
            "stream": False,
            # Keep the model warm so later calls skip the cold-load cost.
            "keep_alive": self.settings.ollama_keep_alive,
        }
        if json_format:
            # Constrain the model to emit syntactically valid JSON (the prompt asks for an array).
            payload["format"] = "json"
        if self.settings.ollama_num_predict > 0:
            payload["options"] = {"num_predict": self.settings.ollama_num_predict}

        try:
            async with httpx.AsyncClient(timeout=self.settings.ollama_timeout_seconds) as client:
                response = await client.post(f"{base_url}/api/chat", json=payload)
                response.raise_for_status()
                content = response.json().get("message", {}).get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        except httpx.HTTPError as exc:
            # Include the exception type — timeouts often have an empty message.
            logger.warning(
                "Ollama request failed for agent %s: %s (%s)",
                self.config.id,
                exc,
                type(exc).__name__,
            )
        return None

    async def _generate_openai(
        self, prompt: str, system: str | None, json_format: bool = False
    ) -> str | None:
        """TODO: OpenAI chat completions."""
        api_key = self._resolve_secret(self.config.api_key_env)
        if not api_key:
            return None
        _ = (prompt, system, json_format, api_key)
        return None

    async def _generate_anthropic(
        self, prompt: str, system: str | None, json_format: bool = False
    ) -> str | None:
        """TODO: Anthropic messages API."""
        api_key = self._resolve_secret(self.config.api_key_env)
        if not api_key:
            return None
        _ = (prompt, system, json_format, api_key)
        return None

    def _resolve_secret(self, env_name: str | None) -> str | None:
        if not env_name:
            return None
        return os.getenv(env_name)
