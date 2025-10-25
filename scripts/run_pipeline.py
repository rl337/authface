"""Entry point used by GitHub Actions to generate data releases."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from collector.config import load_feed_state, load_feeds, save_feed_state
from collector.fetcher import fetch_all
from collector.processor import (
    build_release,
    cluster_entries,
    release_payload,
    update_trust_scores,
)
from collector.summarizer import summarise_clusters


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a correlated news release")
    parser.add_argument(
        "--feeds",
        type=Path,
        default=Path("data/feeds.yaml"),
        help="Path to the feed definition YAML file.",
    )
    parser.add_argument(
        "--feed-state",
        type=Path,
        default=Path("data/feed_state.json"),
        help="Path to the mutable feed state JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/releases"),
        help="Directory that will receive the generated release JSON.",
    )
    parser.add_argument(
        "--model",
        default="sshleifer/distilbart-cnn-12-6",
        help="Hugging Face model used for summarisation.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level.",
    )
    return parser.parse_args()


async def run_pipeline(args: argparse.Namespace) -> Path:
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    feeds = load_feeds(args.feeds)
    feed_state = load_feed_state(args.feed_state, feeds)

    entries = await fetch_all(feeds)
    clustering = cluster_entries(entries)
    summaries = summarise_clusters(clustering.grouped_entries, model_name=args.model)
    update_trust_scores(feed_state, clustering.grouped_entries.items())
    events = build_release(feeds, feed_state, clustering, summaries)
    payload = release_payload(events)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args.output.mkdir(parents=True, exist_ok=True)
    release_path = args.output / f"release-{timestamp}.json"
    release_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    save_feed_state(args.feed_state, feed_state)
    logging.info("Wrote release to %s", release_path)
    return release_path


def main() -> None:
    args = parse_args()
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":  # pragma: no cover
    main()
