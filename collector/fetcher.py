"""Asynchronous feed fetching utilities."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

try:  # pragma: no cover - optional dependency
    import aiohttp
except Exception:  # pragma: no cover - executed when aiohttp is unavailable
    aiohttp = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import feedparser
except Exception:  # pragma: no cover - executed when feedparser is unavailable
    feedparser = None  # type: ignore

from .config import Feed

logger = logging.getLogger(__name__)


@dataclass
class FeedEntry:
    """Normalised representation of a feed item."""

    feed_id: str
    title: str
    summary: str
    published: Optional[str]
    link: Optional[str]
    categories: List[str]
    raw: Dict


async def _fetch_single(session, feed: Feed) -> List[FeedEntry]:
    """Download and parse a single feed."""

    if aiohttp is None or feedparser is None:
        raise RuntimeError("aiohttp and feedparser must be installed to fetch feeds")

    try:
        async with session.get(feed.url, timeout=aiohttp.ClientTimeout(total=20)) as response:
            response.raise_for_status()
            payload = await response.read()
    except Exception as exc:  # pragma: no cover - network errors are logged
        logger.warning("Failed to download %s: %s", feed.url, exc)
        return []

    parsed = feedparser.parse(payload)
    entries: List[FeedEntry] = []
    for entry in parsed.entries:
        title = entry.get("title", "").strip()
        summary = entry.get("summary", "").strip() or entry.get("description", "")
        published = entry.get("published") or entry.get("updated")
        link = entry.get("link")
        categories = [tag.get("term") for tag in entry.get("tags", []) if isinstance(tag, dict)]
        entries.append(
            FeedEntry(
                feed_id=feed.identifier,
                title=title,
                summary=summary,
                published=published,
                link=link,
                categories=[c for c in categories if c],
                raw=entry,
            )
        )
    return entries


async def fetch_all(feeds: List[Feed]) -> List[FeedEntry]:
    """Fetch every feed concurrently and return a flat list of entries."""

    if aiohttp is None:
        raise RuntimeError("aiohttp must be installed to fetch feeds")
    connector = aiohttp.TCPConnector(limit_per_host=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [_fetch_single(session, feed) for feed in feeds]
        results = await asyncio.gather(*tasks)

    entries: List[FeedEntry] = []
    for result in results:
        entries.extend(result)
    logger.info("Fetched %d entries from %d feeds", len(entries), len(feeds))
    return entries


def normalise_timestamp(timestamp: Optional[str]) -> Optional[str]:
    """Convert a feed timestamp into ISO8601."""

    if not timestamp or feedparser is None:
        return timestamp
    try:
        parsed = feedparser.parse(timestamp)
        if parsed.bozo and not getattr(parsed, "modified", None):  # feedparser bozo bit for invalid data
            raise ValueError(parsed.bozo_exception)
        if getattr(parsed, "modified", None):
            dt = datetime(*parsed.modified[:6])
        else:
            return timestamp
    except Exception:  # pragma: no cover - timestamp parsing is best effort
        return timestamp
    return dt.isoformat() + "Z"
