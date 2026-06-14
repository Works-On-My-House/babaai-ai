"""Night-only web crawler for recipe ingestion."""

from app.crawler.scheduler import is_crawl_window

__all__ = ["is_crawl_window"]
