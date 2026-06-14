from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cors_origins: str

    # Service auth
    ai_service_token: str
    core_jwks_url: str

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

    crawler_timezone: str
    crawler_allow_force: bool

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
