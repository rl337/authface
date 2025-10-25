"""Collector package exposing the feed aggregation utilities."""

from .config import Feed, FeedState, load_feed_state, load_feeds, save_feed_state
from .fetcher import FeedEntry, fetch_all
from .processor import (
    ClusteredEvent,
    ClusteringResult,
    build_release,
    cluster_entries,
    release_payload,
    update_trust_scores,
)
from .summarizer import Summarizer, summarise_clusters

__all__ = [
    "Feed",
    "FeedState",
    "load_feeds",
    "load_feed_state",
    "save_feed_state",
    "FeedEntry",
    "fetch_all",
    "ClusteredEvent",
    "ClusteringResult",
    "cluster_entries",
    "update_trust_scores",
    "build_release",
    "release_payload",
    "Summarizer",
    "summarise_clusters",
]
