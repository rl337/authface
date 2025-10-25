"""High-level orchestration utilities for the data correlation pipeline."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import load_feed_state, load_feeds, save_feed_state
from .fetcher import fetch_all
from .processor import build_release, cluster_entries, release_payload, update_trust_scores
from .summarizer import summarise_clusters


async def run_pipeline(
    feeds_path: Path,
    feed_state_path: Path,
    output_dir: Path,
    model_name: str,
) -> Path:
    """Execute the full aggregation pipeline and persist artefacts.

    Args:
        feeds_path: Location of the feed definition YAML file.
        feed_state_path: Location of the mutable feed state JSON file.
        output_dir: Directory that will receive the generated release payload.
        model_name: Hugging Face summarisation model identifier.

    Returns:
        The path to the written release JSON file.
    """

    feeds = load_feeds(feeds_path)
    feed_state = load_feed_state(feed_state_path, feeds)

    entries = await fetch_all(feeds)
    clustering = cluster_entries(entries)
    summaries = summarise_clusters(clustering.grouped_entries, model_name=model_name)
    update_trust_scores(feed_state, clustering.grouped_entries.items())
    events = build_release(feeds, feed_state, clustering, summaries)
    payload = release_payload(events)

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    release_path = output_dir / f"release-{timestamp}.json"
    release_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    save_feed_state(feed_state_path, feed_state)
    return release_path
