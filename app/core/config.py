from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cors_origins: str

    # Service auth (inbound core→ai). We store only the SHA-256 hash of the shared secret (never the
    # plaintext) and verify by hashing the incoming header — same idea as the refresh-token store.
    # (Outbound ai→core uses core_service_token below.)
    ai_service_token_hash: str
    core_jwks_url: str

    # User auth / tier routing
    # Permission claim that grants the premium (fast) model + a daily token quota.
    # Authenticated users without it fall back to the free Ollama tier.
    ai_pro_permission: str = "AI_PRO_SUGGESTIONS"
    premium_agent_id: str = "openai-primary"
    # Daily premium token quota per user; <= 0 disables enforcement.
    premium_daily_token_quota: int = 100_000

    # Core API (crawler ingestion)
    core_base_url: str
    core_service_token: str

    # Qdrant vector store
    qdrant_url: str
    qdrant_collection: str

    # Config paths (bundled defaults; override via env if needed)
    agents_config_path: str = "config/agents.json"
    rag_config_path: str = "config/rag.json"
    crawlers_config_path: str = "config/crawlers.json"
    prompts_config_path: str = "config/prompts.json"

    # Feature flags
    agents_enabled: bool
    rag_enabled: bool
    crawler_enabled: bool
    default_agent_id: str

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    ollama_enabled: bool
    ollama_base_url: str
    ollama_model: str
    # Per-request timeout (s). Fail fast instead of hanging — the caller degrades gracefully.
    ollama_timeout_seconds: float = 45.0
    # Keep the model resident between calls so it isn't reloaded (cold start) each time.
    ollama_keep_alive: str = "30m"
    # Cap generated tokens to bound latency; 0 = no explicit cap (Ollama default).
    ollama_num_predict: int = 0

    crawler_timezone: str
    crawler_allow_force: bool

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
