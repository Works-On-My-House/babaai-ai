import asyncio
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.core.json_config import load_crawlers_config

logger = logging.getLogger(__name__)


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute))


def _resolve_timezone(_config: dict) -> ZoneInfo:
    tz_name = get_settings().crawler_timezone
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def _load_crawler_config() -> dict:
    return load_crawlers_config()


def is_crawl_window(now: datetime | None = None, config: dict | None = None) -> bool:
    """Return True only when local time is within the configured night window.

    Default window: 01:00 inclusive start, 05:30 exclusive end.
    """
    config = config or _load_crawler_config()
    schedule = config.get("schedule", {})
    if not schedule.get("enabled", True):
        return False

    start = _parse_hhmm(schedule.get("start", "01:00"))
    end = _parse_hhmm(schedule.get("end", "05:30"))
    tz = _resolve_timezone(config)

    if now is None:
        now = datetime.now(tz)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)

    current = now.time()
    if start <= end:
        return start <= current < end
    # Overnight window (e.g. 22:00–06:00)
    return current >= start or current < end


async def run_scheduler_loop() -> None:
    """Background loop: wake periodically and run crawler inside night window only."""
    settings = get_settings()
    if not settings.crawler_enabled:
        logger.info("Crawler disabled — scheduler not started")
        return

    config = _load_crawler_config()
    interval = config.get("tick_interval_minutes", 15) * 60

    while True:
        if is_crawl_window(config=config):
            from app.crawler.runner import run_once

            logger.info("Crawl window active — invoking runner")
            await run_once()
        else:
            logger.debug("Outside crawl window — skipping tick")
        await asyncio.sleep(interval)
