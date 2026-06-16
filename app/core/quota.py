"""Daily per-user token quota counters for the premium AI tier.

In-memory stub: a process-local counter keyed by (user_id, UTC date). Not shared across instances
and not persisted across restarts — adequate while premium quotas are inactive (no user holds the
premium permission yet). When premium tiers go live, swap the store here for a shared backend; the
call sites (``get_usage`` / ``record_tokens``) keep their async signatures. See ClickUp 869dqh96c.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

# (user_id, yyyy-mm-dd) -> tokens used today.
_usage: dict[tuple[str, str], int] = {}


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


async def get_usage(user_id: UUID) -> int:
    """Tokens consumed by ``user_id`` so far today."""
    return _usage.get((str(user_id), _today()), 0)


async def record_tokens(user_id: UUID, tokens: int) -> int:
    """Add ``tokens`` to today's counter and return the new running total."""
    key = (str(user_id), _today())
    if tokens > 0:
        _usage[key] = _usage.get(key, 0) + tokens
    return _usage.get(key, 0)
