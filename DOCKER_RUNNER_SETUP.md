# Docker-Based Self-Hosted Runner Setup

## Architecture

```
Host Machine
├── Docker Container (GitHub Actions Runner)
│   └── /app/models (inside container)
│           ↓ mounted to
└── /var/models (on host, persistent storage)
```

## Benefits

1. **Persistent Storage**: Models stored on host filesystem, survive container restarts
2. **Easy Updates**: Update runner software by rebuilding image, models stay intact
3. **Portable**: Container is self-contained except for model volume
4. **Fast Access**: Direct file access to host storage
5. **Multiple Containers**: Could share same model volume if needed

## Setup

### 1. Create Dockerfile for Runner

```dockerfile
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3.12 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create work directory
WORKDIR /runner

# Copy runner setup script
COPY setup-runner.sh .

# Download and configure GitHub Actions runner
RUN chmod +x setup-runner.sh

# Set up model directory
RUN mkdir -p /app/models

# Environment for model cache
ENV TRANSFORMERS_CACHE=/app/models
ENV HF_HOME=/app/models

CMD ["./run.sh"]
```

### 2. Create Host Directory Structure

```bash
# On your host machine
mkdir -p /var/github-runners/weirdness/models
chmod 755 /var/github-runners/weirdness/models
```

### 3. Runner Setup Script

```bash
#!/bin/bash
# setup-runner.sh

RUNNER_VERSION="2.311.0"

# Download runner
curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz \
  -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

tar xzf ./actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
./bin/installdependencies.sh
```

### 4. Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  github-runner:
    build: .
    container_name: weirdness-runner
    restart: unless-stopped
    volumes:
      # Models persist on host
      - /var/github-runners/weirdness/models:/app/models
      # Runner work directory (optional, for persistence)
      - ./runner:/runner/_work
    environment:
      - TRANSFORMERS_CACHE=/app/models
      - HF_HOME=/app/models
      - RUNNER_TOKEN=${RUNNER_TOKEN}
      - GITHUB_REPO=https://github.com/rl337/weirdness
    network_mode: host  # Or bridge with proper networking
```

### 5. Start Runner

```bash
# Get token from GitHub:
# Settings → Actions → Runners → New self-hosted runner

# Set token as environment variable
export RUNNER_TOKEN=your_token_here

# Start container
docker-compose up -d

# Configure runner inside container
docker exec -it weirdness-runner bash
cd /runner
./config.sh --url https://github.com/rl337/weirdness --token $RUNNER_TOKEN
./run.sh
```

### 6. Update Your Workflow

```yaml
# .github/workflows/data-release.yml
jobs:
  build-and-release:
    runs-on: self-hosted  # Will use your container
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: uv sync
      - name: Run data aggregation pipeline
        run: uv run python scripts/run_pipeline.py --log-level INFO
        env:
          TRANSFORMERS_CACHE: /app/models
          HF_HOME: /app/models
```

## First Run Behavior

### First Time
1. Container starts, `/app/models` is empty
2. Pipeline runs, downloads models to `/app/models`
3. Models saved to `/var/models` on host (via volume mount)

### Subsequent Runs
1. Container starts or restarts
2. `/app/models` is mounted from host (models already there!)
3. Pipeline runs instantly, no download needed
4. Models persist across container restarts

## Maintenance

### Update Runner Software

```bash
# Stop container
docker-compose down

# Pull new runner version in Dockerfile
# Rebuild image
docker-compose build

# Start again (models still there!)
docker-compose up -d
```

### Inspect Models

```bash
# Check models on host
ls -lh /var/github-runners/weirdness/models/

# Inside container
docker exec -it weirdness-runner ls -lh /app/models
```

### Backup Models

```bash
# Models are just files on host
tar czf models-backup.tar.gz /var/github-runners/weirdness/models/
```

## Alternative: Pre-populate Models

Even better - populate models before first run:

```dockerfile
# In Dockerfile, after setting up Python
RUN pip install transformers torch

# Pre-download models into /app/models
RUN python -c "from transformers import pipeline; pipeline('summarization', model='sshleifer/distilbart-cnn-12-6')"

# Models go into image layer
# But still use volume mount for persistence across image updates
```

## Volume Mount Strategy

You have two options:

### Option A: Mount models directory
```yaml
volumes:
  - /var/models:/app/models
```
- Models persist on host
- Survive container rebuilds
- Can backup/migrate easily

### Option B: Mount entire cache directory
```yaml
volumes:
  - /var/cache:/root/.cache
```
- Includes all Python caches
- Faster everything, not just models
- Larger volume, more to backup

## Network Considerations

For pulling from GitHub:
```yaml
network_mode: host  # Simplest, uses host network directly
```

Or bridge with DNS:
```yaml
networks:
  default:
    external: true
    name: mynetwork
```

