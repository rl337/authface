import json
from pathlib import Path

import pytest

from collector.config import Feed, FeedState, load_feed_state, save_feed_state
from collector.fetcher import FeedEntry
from collector.processor import (
    ClusteringResult,
    build_release,
    cluster_entries,
    release_payload,
    update_trust_scores,
)


def make_entry(feed_id: str, title: str, summary: str) -> FeedEntry:
    return FeedEntry(
        feed_id=feed_id,
        title=title,
        summary=summary,
        published="2024-05-01T00:00:00Z",
        link="https://example.com",
        categories=[],
        raw={},
    )


def test_cluster_entries_groups_similar_content():
    entries = [
        make_entry("a", "Storm hits Oklahoma", "A tornado touched down in Oklahoma City."),
        make_entry("b", "Oklahoma tornado", "Emergency services respond to Oklahoma tornado."),
        make_entry("c", "Sports update", "A different topic entirely."),
    ]
    result = cluster_entries(entries)
    assert isinstance(result, ClusteringResult)
    cluster_sizes = sorted(len(group) for group in result.grouped_entries.values())
    assert cluster_sizes == [1, 2]


def test_update_trust_scores_increases_on_correlation():
    entries = [
        make_entry("trusted", "Storm hits", ""),
        make_entry("other", "Storm update", ""),
    ]
    result = cluster_entries(entries)
    feed_state = {
        "trusted": FeedState(identifier="trusted", trust_score=0.5),
        "other": FeedState(identifier="other", trust_score=0.5),
    }
    update_trust_scores(feed_state, result.grouped_entries.items(), correlation_bonus=0.1)
    assert feed_state["trusted"].trust_score > 0.5
    assert feed_state["other"].trust_score > 0.5


def test_release_payload_structure(tmp_path: Path):
    feeds = [
        Feed(
            identifier="a",
            url="https://example.com/a",
            feed_type="rss",
            discovery="manual",
            geography="US",
            base_trust=0.5,
        ),
        Feed(
            identifier="b",
            url="https://example.com/b",
            feed_type="rss",
            discovery="manual",
            geography="US",
            base_trust=0.5,
        ),
    ]
    feed_state = {feed.identifier: FeedState(feed.identifier, 0.6) for feed in feeds}
    entries = [
        make_entry("a", "Storm hits Oklahoma", "A tornado touched down in Oklahoma City."),
        make_entry("b", "Oklahoma tornado", "Emergency services respond to Oklahoma tornado."),
    ]
    clustering = cluster_entries(entries)
    summaries = {next(iter(clustering.grouped_entries.keys())): "Storm summary"}
    events = build_release(feeds, feed_state, clustering, summaries)
    payload = release_payload(events)
    assert "generated_at" in payload
    assert len(payload["events"]) == len(events)
    assert payload["events"][0]["summary"] == "Storm summary"


@pytest.mark.parametrize("initial_state", [{}, {"feed": {"trust_score": 0.9, "last_seen": None}}])
def test_feed_state_roundtrip(tmp_path: Path, initial_state):
    feeds = [Feed("feed", "https://example.com", "rss", "manual", "US", 0.5)]
    path = tmp_path / "state.json"
    if initial_state:
        path.write_text(json.dumps(initial_state))
    state = load_feed_state(path, feeds)
    state["feed"].trust_score = 0.77
    save_feed_state(path, state)
    saved = json.loads(path.read_text())
    assert pytest.approx(saved["feed"]["trust_score"], rel=1e-3) == 0.77

def test_update_trust_scores_penalises_isolated_entries():
    entries = [make_entry("solo", "Unique story", "" )]
    feed_state = {"solo": FeedState(identifier="solo", trust_score=0.05)}
    update_trust_scores(feed_state, [(0, entries)], isolation_penalty=0.1)
    assert feed_state["solo"].trust_score == 0.0


def test_update_trust_scores_clamps_upper_bound():
    entries = [
        make_entry("a", "Shared event", ""),
        make_entry("b", "Shared event", ""),
    ]
    feed_state = {
        "a": FeedState(identifier="a", trust_score=0.98),
        "b": FeedState(identifier="b", trust_score=0.99),
    }
    update_trust_scores(feed_state, [(0, entries)], correlation_bonus=0.1)
    assert feed_state["a"].trust_score == pytest.approx(1.0)
    assert feed_state["b"].trust_score == pytest.approx(1.0)
