"""Summarisation helpers backed by Hugging Face transformers."""
from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional

from .fetcher import FeedEntry

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from transformers import pipeline
except Exception:  # pragma: no cover - executed when transformers is unavailable
    pipeline = None  # type: ignore


class Summarizer:
    """Lazy wrapper around the transformers summarisation pipeline."""

    def __init__(self, model_name: str = "sshleifer/distilbart-cnn-12-6") -> None:
        self.model_name = model_name
        self._pipeline: Optional[object] = None

    def ensure_loaded(self) -> None:
        if self._pipeline is None and pipeline is not None:
            logger.info("Loading summarisation model %s", self.model_name)
            self._pipeline = pipeline("summarization", model=self.model_name)
        elif pipeline is None and self._pipeline is None:
            logger.warning(
                "transformers is unavailable; falling back to extractive summaries"
            )
            self._pipeline = False  # sentinel indicating fallback mode

    def summarize_cluster(self, cluster_index: int, entries: Iterable[FeedEntry]) -> str:
        texts: List[str] = []
        for entry in entries:
            content = " ".join(part for part in [entry.title, entry.summary] if part)
            if content:
                texts.append(content)
        if not texts:
            return ""
        self.ensure_loaded()
        if self._pipeline and pipeline is not None:
            combined = "\n".join(texts[:5])
            result = self._pipeline(
                combined,
                max_length=130,
                min_length=30,
                do_sample=False,
            )
            summary = result[0]["summary_text"].strip()
        else:
            summary = " ".join(texts)[:280]
        logger.debug("Summary for cluster %s: %s", cluster_index, summary)
        return summary


def summarise_clusters(clusters: Dict[int, List[FeedEntry]], model_name: str) -> Dict[int, str]:
    summarizer = Summarizer(model_name=model_name)
    summaries: Dict[int, str] = {}
    for cluster_index, entries in clusters.items():
        summaries[cluster_index] = summarizer.summarize_cluster(cluster_index, entries)
    return summaries
