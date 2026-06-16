import hashlib
import os

os.environ.update(
    {
        "TESTING": "1",
        "CORS_ORIGINS": "http://localhost:5173",
        # ai stores only the hash of the service secret; tests send the raw "test-ai-token".
        "AI_SERVICE_TOKEN_HASH": hashlib.sha256(b"test-ai-token").hexdigest(),
        "CORE_JWKS_URL": "http://localhost:8081/.well-known/jwks.json",
        "CORE_BASE_URL": "http://localhost:8081",
        "CORE_SERVICE_TOKEN": "test-ai-token",
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_COLLECTION": "recipe_chunks",
        "AGENTS_ENABLED": "false",
        "RAG_ENABLED": "true",
        "CRAWLER_ENABLED": "false",
        "DEFAULT_AGENT_ID": "ollama-local",
        "OLLAMA_ENABLED": "true",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "llama3.2",
        "CRAWLER_TIMEZONE": "Europe/Sofia",
        "CRAWLER_ALLOW_FORCE": "false",
    }
)

from app.core.config import get_settings

get_settings.cache_clear()
