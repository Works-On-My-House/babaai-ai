"""Crawler orchestration — discover → fetch → parse → normalize → save → reindex."""

import argparse
import asyncio
import logging

from app.core.config import get_settings
from app.crawler.scheduler import is_crawl_window

logger = logging.getLogger(__name__)


async def run_once(*, force: bool = False) -> None:
    """TODO: orchestrate full crawl pipeline. Stubs log intent for now."""
    settings = get_settings()
    if not force and not is_crawl_window():
        logger.info("Outside crawl window — run_once skipped")
        return
    if force and not settings.crawler_allow_force:
        logger.warning("Force crawl blocked — set CRAWLER_ALLOW_FORCE=true for dev override")
        return

    logger.info("TODO: crawl pipeline — discover, fetch, parse, normalize, dedup, save, reindex")
    # TODO: discover_urls() → fetch_page() → parse_recipe_json_ld() → normalize → persist


def main() -> None:
    parser = argparse.ArgumentParser(description="Run crawler once")
    parser.add_argument("--force", action="store_true", help="Bypass night window (dev only)")
    args = parser.parse_args()
    asyncio.run(run_once(force=args.force))


if __name__ == "__main__":
    main()
