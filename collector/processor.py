"""Core logic for correlating feed entries and producing releases."""
from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Sequence, Tuple

from .config import Feed, FeedState
from .fetcher import FeedEntry, normalise_timestamp

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "the",
    "a",
    "an",
    "in",
    "on",
    "and",
    "or",
    "for",
    "to",
    "of",
    "is",
    "are",
    "with",
    "by",
    "from",
    "at",
    "as",
    "be",
    "this",
    "that",
    "it",
    "its",
    "was",
    "were",
    "has",
    "have",
    "had",
}


@dataclass
class ClusteredEvent:
    """Structured representation of a correlated event."""

    cluster_id: str
    summary: str
    keywords: List[str]
    confidence: float
    feeds: List[Dict]
    locations: List[str]


@dataclass
class ClusteringResult:
    """Return value for ``cluster_entries`` containing metadata."""

    grouped_entries: Dict[int, List[FeedEntry]]
    tokens: List[Counter]
    entry_index: Dict[int, int]


def _prepare_documents(entries: Sequence[FeedEntry]) -> List[str]:
    documents: List[str] = []
    for item in entries:
        doc = " ".join(part for part in [item.title, item.summary] if part).strip()
        documents.append(doc or item.title or "")
    return documents


def _tokenize(text: str) -> Counter:
    words = re.findall(r"[a-z0-9]+", text.lower())
    filtered = [word for word in words if word not in _STOPWORDS]
    return Counter(filtered)


def _jaccard(a: Counter, b: Counter) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 1.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def cluster_entries(entries: Sequence[FeedEntry], similarity_threshold: float = 0.2) -> ClusteringResult:
    """Group similar entries together using a lightweight Jaccard heuristic."""

    if not entries:
        return ClusteringResult({}, [], {})

    documents = _prepare_documents(entries)
    tokens = [_tokenize(doc) for doc in documents]
    grouped_entries: Dict[int, List[FeedEntry]] = {}
    member_indices: Dict[int, List[int]] = {}
    entry_index = {id(entry): idx for idx, entry in enumerate(entries)}

    for idx, entry in enumerate(entries):
        best_cluster = None
        best_similarity = 0.0
        for cluster_id, indices in member_indices.items():
            similarity = max(_jaccard(tokens[idx], tokens[member]) for member in indices)
            if similarity >= similarity_threshold and similarity > best_similarity:
                best_cluster = cluster_id
                best_similarity = similarity
        if best_cluster is None:
            cluster_id = len(grouped_entries)
            grouped_entries[cluster_id] = [entry]
            member_indices[cluster_id] = [idx]
        else:
            grouped_entries[best_cluster].append(entry)
            member_indices[best_cluster].append(idx)

    logger.info("Clustered %d entries into %d groups", len(entries), len(grouped_entries))
    return ClusteringResult(grouped_entries, tokens, entry_index)


def _extract_keywords(tokens: List[Counter], indices: Sequence[int]) -> List[str]:
    if not indices:
        return []
    aggregate: Counter = Counter()
    for idx in indices:
        aggregate.update(tokens[idx])
    most_common = [word for word, _ in aggregate.most_common(5)]
    return most_common


def _cluster_locations(entries: Sequence[FeedEntry], feed_lookup: Dict[str, Feed]) -> List[str]:
    locations: List[str] = []
    for entry in entries:
        feed = feed_lookup.get(entry.feed_id)
        if feed and feed.geography and feed.geography not in locations:
            locations.append(feed.geography)
    return locations


def _calculate_confidence(entries: Sequence[FeedEntry], feed_state: Dict[str, FeedState]) -> float:
    if not entries:
        return 0.0
    scores = [feed_state[entry.feed_id].trust_score for entry in entries if entry.feed_id in feed_state]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def update_trust_scores(
    feed_state: Dict[str, FeedState],
    clustered_entries: Iterable[Tuple[int, List[FeedEntry]]],
    correlation_bonus: float = 0.02,
    isolation_penalty: float = 0.01,
) -> None:
    """Adjust trust scores based on entry correlation."""

    for _, entries in clustered_entries:
        feed_ids = {entry.feed_id for entry in entries}
        if len(feed_ids) > 1:
            for feed_id in feed_ids:
                feed_state[feed_id].trust_score = min(
                    1.0, feed_state[feed_id].trust_score + correlation_bonus
                )
        elif feed_ids:
            feed_id = next(iter(feed_ids))
            feed_state[feed_id].trust_score = max(
                0.0, feed_state[feed_id].trust_score - isolation_penalty
            )


def build_release(
    feeds: Iterable[Feed],
    feed_state: Dict[str, FeedState],
    clustering: ClusteringResult,
    summaries: Dict[int, str],
) -> List[ClusteredEvent]:
    """Transform clustered entries into release objects."""

    feed_lookup = {feed.identifier: feed for feed in feeds}
    events: List[ClusteredEvent] = []
    for cluster_index, entries in clustering.grouped_entries.items():
        token_indices = [clustering.entry_index[id(entry)] for entry in entries]
        keywords = _extract_keywords(clustering.tokens, token_indices)
        locations = _cluster_locations(entries, feed_lookup)
        confidence = _calculate_confidence(entries, feed_state)
        feeds_payload: List[Dict] = []
        for entry in entries:
            feeds_payload.append(
                {
                    "feed_id": entry.feed_id,
                    "title": entry.title,
                    "summary": entry.summary,
                    "published": normalise_timestamp(entry.published),
                    "link": entry.link,
                    "categories": entry.categories,
                    "trust_score": feed_state[entry.feed_id].trust_score,
                }
            )
            feed_state[entry.feed_id].last_seen = normalise_timestamp(entry.published)
        cluster_id = f"cluster-{cluster_index}"
        summary = summaries.get(cluster_index, "")
        events.append(
            ClusteredEvent(
                cluster_id=cluster_id,
                summary=summary,
                keywords=keywords,
                confidence=confidence,
                feeds=feeds_payload,
                locations=locations,
            )
        )
    return events


def release_payload(events: Sequence[ClusteredEvent]) -> Dict:
    """Generate the final JSON payload."""

    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "generated_at": timestamp,
        "events": [
            {
                "id": event.cluster_id,
                "summary": event.summary,
                "keywords": event.keywords,
                "confidence": round(event.confidence, 4),
                "feeds": event.feeds,
                "locations": event.locations,
            }
            for event in events
        ],
    }
