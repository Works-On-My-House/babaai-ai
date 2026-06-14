from app.agents.registry import AgentRegistry
from app.core.json_config import load_agents_config, load_rag_config


def test_load_agents_config():
    config = load_agents_config()
    assert "agents" in config
    assert len(config["agents"]) == 3
    assert "routing" in config


def test_load_rag_config():
    config = load_rag_config()
    assert config["chunk_size"] == 512
    assert config["top_k"] == 5


def test_agent_registry_routing_chain():
    registry = AgentRegistry()
    chain = registry.routing_chain("rag_qa")
    assert chain == ["openai-primary", "ollama-local"]
