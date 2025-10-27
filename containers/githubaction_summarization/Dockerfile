FROM alpine:latest

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
    gcc \
    g++ \
    musl-dev \
    linux-headers

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

# Create directories
RUN mkdir -p /app/models /app/api /runner

# Set environment variables
ENV TRANSFORMERS_CACHE=/app/models \
    HF_HOME=/app/models \
    PYTHONPATH=/app/models/.site-packages

# Copy project files
COPY pyproject.toml .python-version /app/
COPY collector /app/collector

# Copy runner scripts (from container directory, build context is repo root)
COPY containers/githubaction_summarization/setup-runner.sh /runner/setup-runner.sh
COPY containers/githubaction_summarization/entrypoint.sh /runner/entrypoint.sh
RUN chmod +x /runner/setup-runner.sh /runner/entrypoint.sh

# Copy API server (from container directory, build context is repo root)
COPY containers/githubaction_summarization/api-server.py /app/api/api-server.py

# Install Python dependencies
RUN pip3 install --no-cache-dir aiohttp feedparser PyYAML transformers torch numpy flask

# Expose health endpoints
EXPOSE 8080

WORKDIR /runner
ENTRYPOINT ["/runner/entrypoint.sh"]

