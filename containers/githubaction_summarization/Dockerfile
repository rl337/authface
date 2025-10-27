FROM rl337/callableapis:base

# Metadata
LABEL maintainer="rl337"
LABEL description="GitHub Actions self-hosted runner for weirdness data pipeline"
LABEL container="weirdness-githubaction"

# Install system dependencies
RUN apk add --no-cache \
    bash \
    curl \
    git \
    python3 \
    python3-dev \
    py3-pip \
    py3-virtualenv \
    gcc \
    g++ \
    musl-dev \
    linux-headers

# Install uv for faster Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

# Create directories
WORKDIR /app
RUN mkdir -p /app/models /app/api

# Set environment variables for model caching
ENV TRANSFORMERS_CACHE=/app/models
ENV HF_HOME=/app/models
ENV PYTHONPATH=/app/models/.site-packages:$PYTHONPATH

# Copy project files
COPY ../../pyproject.toml ../../.python-version ./
COPY ../../collector ./collector

# Setup GitHub Actions Runner
WORKDIR /runner

# Copy runner setup script
COPY setup-runner.sh .
RUN chmod +x setup-runner.sh

# Install Python dependencies with uv
RUN uv pip install --system aiohttp feedparser PyYAML transformers torch numpy flask

# Copy API server and entrypoint
COPY api-server.py /app/api/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expose health and status endpoints
EXPOSE 8080

ENTRYPOINT ["/runner/entrypoint.sh"]

