from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Dict, List

import pytest

from collector.config import Feed
from collector.fetcher import FeedEntry, fetch_all


class DummyResponse:
    def __init__(self, url: str, payloads: Dict[str, bytes], calls: List[str]):
        self._url = url
        self._payloads = payloads
        self._calls = calls

    async def __aenter__(self) -> "DummyResponse":
        self._calls.append(self._url)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def read(self) -> bytes:
        return self._payloads[self._url]


class DummySession:
    def __init__(self, payloads: Dict[str, bytes], calls: List[str]):
        self._payloads = payloads
        self._calls = calls

    async def __aenter__(self) -> "DummySession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str, timeout=None) -> DummyResponse:
        return DummyResponse(url, self._payloads, self._calls)


def _install_fetcher_dependencies(monkeypatch: pytest.MonkeyPatch, payloads: Dict[str, bytes], calls: List[str]) -> None:
    class DummyConnector:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class DummyTimeout:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    dummy_session = DummySession(payloads, calls)
    monkeypatch.setattr(
        "collector.fetcher.aiohttp",
        SimpleNamespace(
            TCPConnector=lambda **kwargs: DummyConnector(**kwargs),
            ClientSession=lambda connector: dummy_session,
            ClientTimeout=lambda **kwargs: DummyTimeout(**kwargs),
        ),
    )


def test_fetch_all_requests_each_feed(monkeypatch):
    feeds = [
        Feed("one", "https://example.com/one", "rss", "manual", "US", 0.5),
        Feed("two", "https://example.com/two", "rss", "manual", "US", 0.5),
    ]
    payloads = {
        feeds[0].url: b"one",
        feeds[1].url: b"two",
    }
    calls: List[str] = []
    _install_fetcher_dependencies(monkeypatch, payloads, calls)

    def fake_parse(data: bytes) -> SimpleNamespace:
        text = data.decode()
        entries = [
            {
                "title": f"Title {text}",
                "summary": f"Summary {text}",
                "link": f"https://example.com/{text}",
                "tags": [],
            }
        ]
        return SimpleNamespace(entries=entries)

    monkeypatch.setattr("collector.fetcher.feedparser", SimpleNamespace(parse=fake_parse))

    entries = asyncio.run(fetch_all(feeds))
    assert {entry.feed_id for entry in entries} == {"one", "two"}
    assert calls == [feeds[0].url, feeds[1].url]


def test_fetch_all_merges_entries(monkeypatch):
    feeds = [Feed("one", "https://example.com/one", "rss", "manual", "US", 0.5)]
    payloads = {feeds[0].url: b"data"}
    calls: List[str] = []
    _install_fetcher_dependencies(monkeypatch, payloads, calls)

    def fake_parse(data: bytes) -> SimpleNamespace:
        return SimpleNamespace(
            entries=[
                {
                    "title": "Title",
                    "summary": "Summary",
                    "link": "https://example.com/item",
                    "tags": [{"term": "news"}],
                },
                {
                    "title": "Second",
                    "description": "Description",
                    "link": "https://example.com/second",
                    "tags": [{"term": "update"}],
                },
            ]
        )

    monkeypatch.setattr("collector.fetcher.feedparser", SimpleNamespace(parse=fake_parse))

    entries = asyncio.run(fetch_all(feeds))
    assert len(entries) == 2
    assert all(isinstance(entry, FeedEntry) for entry in entries)
    assert entries[0].categories == ['news']
    assert entries[1].categories == ["update"]
