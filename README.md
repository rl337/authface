# Data correlation pipeline

> **Repository description:** GitHub Actions pipeline that polls trusted public feeds twice
> daily, correlates overlapping stories, and publishes structured releases with evolving
> trust scores for each source.

This repository hosts an automated pipeline that polls trusted public feeds, correlates
related stories, and emits structured data releases twice per day. GitHub Actions runs the
pipeline on a fixed schedule to keep the feed trust scores and aggregated reports current.

## What the pipeline does

1. **Collect** – `scripts/run_pipeline.py` downloads each feed listed in
   `data/feeds.yaml` concurrently. The feeds include RSS, Atom, and other structured
   formats from weather, news, and trend sources.
2. **Correlate** – entries are vectorised with TF–IDF and clustered with DBSCAN to detect
   stories that multiple feeds are discussing.
3. **Summarise** – a lightweight Hugging Face summarisation model
   (`sshleifer/distilbart-cnn-12-6`) condenses each cluster into a readable synopsis.
4. **Score trust** – feeds that corroborate other sources receive a trust bonus while
   isolated stories incur a small penalty. Persisted trust levels live in
   `data/feed_state.json` and are updated every run.
5. **Publish** – the structured release is written to `data/releases/` with metadata about
   the feeds, correlated keywords, geographic hints, and confidence scores.

## Repository layout

```
collector/              # Core Python package for the pipeline
  config.py             # Feed definition + state helpers
  fetcher.py            # Asynchronous fetching and normalisation
  processor.py          # Clustering, trust scoring, and payload assembly
  summarizer.py         # Hugging Face-backed cluster summaries
scripts/run_pipeline.py # CLI entry point invoked by CI or locally
data/feeds.yaml         # Curated feed catalogue with metadata
```

## Running locally

Create a Python virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then execute the pipeline:

```bash
python scripts/run_pipeline.py --log-level DEBUG
```

A new release file will be created under `data/releases/`, and the feed trust state will be
persisted to `data/feed_state.json`.

### Tests

The repository ships with pytest-based unit tests covering clustering and state
management:

```bash
pytest
```

## Scheduled automation

`.github/workflows/data-release.yml` provisions a twice-daily GitHub Actions run. The job
performs the following steps:

- installs Python dependencies,
- executes the aggregation pipeline,
- runs the unit test suite, and
- commits updated release artefacts back to the repository (if anything changed).

Every run also uploads the generated releases as workflow artefacts for downstream
processing.

## Extending the feed catalogue

Append new sources to `data/feeds.yaml` with their metadata, including discovery method,
feed type, and any geographical hints. The next scheduled run will begin tracking the feed
and adjust its trust score over time as it correlates (or fails to correlate) with other
sources.
