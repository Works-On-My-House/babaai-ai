from datetime import datetime
from zoneinfo import ZoneInfo

from app.crawler.scheduler import is_crawl_window

CRAWLER_CONFIG = {
    "schedule": {
        "enabled": True,
        "start": "01:00",
        "end": "05:30",
        "timezone_env": "CRAWLER_TIMEZONE",
    }
}


def test_is_crawl_window_inside_night_hours():
    tz = ZoneInfo("UTC")
    inside = datetime(2026, 6, 7, 2, 0, tzinfo=tz)
    assert is_crawl_window(now=inside, config=CRAWLER_CONFIG) is True


def test_is_crawl_window_outside_night_hours():
    tz = ZoneInfo("UTC")
    outside = datetime(2026, 6, 7, 10, 0, tzinfo=tz)
    assert is_crawl_window(now=outside, config=CRAWLER_CONFIG) is False


def test_is_crawl_window_respects_disabled_schedule():
    tz = ZoneInfo("UTC")
    inside = datetime(2026, 6, 7, 2, 0, tzinfo=tz)
    disabled_config = {**CRAWLER_CONFIG, "schedule": {**CRAWLER_CONFIG["schedule"], "enabled": False}}
    assert is_crawl_window(now=inside, config=disabled_config) is False
