from app.core.json_config import load_crawlers_config


def discover_urls() -> list[str]:
    """TODO: seed URLs and allowlisted domain search for recipe pages."""
    config = load_crawlers_config()
    _ = config.get("allowed_domains", [])
    return []
