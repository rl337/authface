FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3.12 \
    python3-pip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

# Install uv dependencies for the weirdness project
WORKDIR /workspace
COPY ../../pyproject.toml ../../.python-version ./
COPY ../../collector ./collector

# Create model cache directory
RUN mkdir -p /app/models

# Set environment variables for model caching
ENV TRANSFORMERS_CACHE=/app/models
ENV HF_HOME=/app/models
ENV PIP_CACHE_DIR=/app/models/.pip_cache

# Setup GitHub Actions Runner
WORKDIR /runner

# Copy runner setup script
COPY setup-runner.sh .
RUN chmod +x setup-runner.sh

# Pre-download Python dependencies (optional, speeds up first run)
RUN pip3 install httpx aiohttp feedparser PyYAML transformers torch numpy --target /app/models/.site-packages
ENV PYTHONPATH=/app/models/.site-packages:$PYTHONPATH

# Create entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/runner/entrypoint.sh"]

