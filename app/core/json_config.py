import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _resolve_path(path: str) -> Path:
    config_path = Path(path)
    if config_path.is_absolute():
        return config_path
    backend_root = Path(__file__).resolve().parents[2]
    return backend_root / config_path


@lru_cache
def _load_json(path: str) -> dict[str, Any]:
    resolved = _resolve_path(path)
    with resolved.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_agents_config() -> dict[str, Any]:
    return _load_json(get_settings().agents_config_path)


def load_rag_config() -> dict[str, Any]:
    return _load_json(get_settings().rag_config_path)


def load_crawlers_config() -> dict[str, Any]:
    return _load_json(get_settings().crawlers_config_path)


def load_prompts_config() -> dict[str, Any]:
    return _load_json(get_settings().prompts_config_path)
