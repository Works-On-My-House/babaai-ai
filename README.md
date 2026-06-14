# BabaAI AI Service

Python FastAPI service — LLM recipe proposals, RAG over Qdrant, and crawler stubs.

Domain data (users, pantry, recipes) lives in **babaai-core**; this service handles intelligence only.

## Prerequisites

- Docker, or Python 3.14+ for local dev
- **core** running on `:8081` (JWKS + recipe ingestion)
- Optional: Ollama for local LLM

## Quick start (Docker)

Includes Qdrant.

```bash
cp .env.example .env
docker compose up --build
```

AI API: http://localhost:8082  
Health: http://localhost:8082/api/v1/health

## Optional: Ollama (local LLM)

Run separately so models persist across restacks:

```bash
docker compose -f docker-compose.ollama.yml up -d
docker exec -it babaai-ollama ollama pull llama3.2
```

## Full stack startup order

1. **babaai-core**
2. **babaai-ai** (this repo)
3. **babaai-gateway**
4. **babaai-frontend**

Set the same `AI_SERVICE_TOKEN` here and in **babaai-core** `.env`.

## Config

JSON configs in `config/`:

- `agents.json` — LLM providers
- `prompts.json` — prompt templates
- `rag.json` — vector retrieval settings
- `crawlers.json` — crawler sources (stubs)

## Environment

| Variable | Description |
|----------|-------------|
| `AI_SERVICE_TOKEN` | Must match core |
| `CORE_JWKS_URL` | JWT validation |
| `CORE_BASE_URL` | Recipe fetch for RAG indexing |
| `QDRANT_URL` | Vector store (set automatically in compose) |
| `OLLAMA_*` | Local LLM settings |

## Tests

```bash
pip install -r requirements.txt
pytest
```
