"""Configuration helpers for the feed aggregation pipeline."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:  # pragma: no cover - optional dependency
    import yaml
except Exception:  # pragma: no cover - executed when PyYAML is unavailable
    yaml = None  # type: ignore


@dataclass
class Feed:
    """Metadata describing a single feed source."""

    identifier: str
    url: str
    feed_type: str
    discovery: str
    geography: Optional[str]
    base_trust: float


@dataclass
class FeedState:
    """Mutable state associated with a feed."""

    identifier: str
    trust_score: float
    last_seen: Optional[str] = None


def _fallback_yaml_parse(text: str) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    current: Optional[Dict[str, object]] = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            if current:
                records.append(current)
            current = {}
            line = line[2:]
            if not line:
                continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        parsed: object
        if value.lower() in {"null", "none", "~"}:
            parsed = None
        elif value.lower() in {"true", "false"}:
            parsed = value.lower() == "true"
        else:
            try:
                parsed = int(value)
            except ValueError:
                try:
                    parsed = float(value)
                except ValueError:
                    parsed = value.strip('"')
        if current is None:
            current = {}
        current[key] = parsed
    if current:
        records.append(current)
    return records


def load_feeds(path: Path) -> List[Feed]:
    """Load the static feed definitions from ``feeds.yaml``."""

    text = path.read_text()
    if yaml is not None:  # pragma: no cover - executed when PyYAML is present
        raw = yaml.safe_load(text)
    else:
        raw = _fallback_yaml_parse(text)
    feeds: List[Feed] = []
    for entry in raw:
        feeds.append(
            Feed(
                identifier=str(entry["id"]),
                url=str(entry["url"]),
                feed_type=str(entry.get("type", "unknown")),
                discovery=str(entry.get("discovery", "unknown")),
                geography=entry.get("geography"),
                base_trust=float(entry.get("trust", 0.5)),
            )
        )
    return feeds


def load_feed_state(path: Path, feeds: Iterable[Feed]) -> Dict[str, FeedState]:
    """Load persisted feed trust scores."""

    if not path.exists():
        return {
            feed.identifier: FeedState(identifier=feed.identifier, trust_score=feed.base_trust)
            for feed in feeds
        }

    data = json.loads(path.read_text())
    state: Dict[str, FeedState] = {}
    for feed in feeds:
        info = data.get(feed.identifier)
        if info is None:
            trust = feed.base_trust
            last_seen = None
        else:
            trust = float(info.get("trust_score", feed.base_trust))
            last_seen = info.get("last_seen")
        state[feed.identifier] = FeedState(
            identifier=feed.identifier,
            trust_score=trust,
            last_seen=last_seen,
        )
    return state


def save_feed_state(path: Path, state: Dict[str, FeedState]) -> None:
    """Persist the updated feed state to disk."""

    serialised = {
        feed_id: {
            "trust_score": round(info.trust_score, 4),
            "last_seen": info.last_seen,
        }
        for feed_id, info in state.items()
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(serialised, indent=2, sort_keys=True))
