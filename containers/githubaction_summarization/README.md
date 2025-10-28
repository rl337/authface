# GitHub Actions Self-Hosted Runner

This container runs a self-hosted GitHub Actions runner for the weirdness data pipeline. It includes persistent model caching to avoid re-downloading transformers models on every run.

## Architecture

```
GitHub.com (orchestrator)
    ↓
Docker Container (this)
    ├── GitHub Actions Runner Agent
    ├── Python Environment
    └── /app/models (mounted from host)
```

## Setup

### 1. Get Runner Token

1. Go to: https://github.com/rl337/weirdness/settings/actions/runners/new
2. Choose "New self-hosted runner"
3. Copy the runner token

### 2. Configure Environment

```bash
cd containers/githubaction_summarization
cp .env.example .env
# Edit .env and add your RUNNER_TOKEN
```

### 3. Create Host Directories

```bash
mkdir -p models work
chmod 755 models work
```

### 4. Build and Start

```bash
docker-compose build
docker-compose up -d
```

### 5. Check Logs

```bash
docker-compose logs -f github-runner
```

## How It Works

### First Run
1. Container starts
2. Runner registers with GitHub
3. Pipeline workflow triggers
4. Models download to `/app/models` (mounted to `./models` on host)
5. Pipeline completes

### Subsequent Runs
1. Container starts
2. Models already exist in `./models`
3. Pipeline runs instantly (no download)
4. Much faster execution

## Persistence

Models are stored on the host in:
- `./models/` - Hugging Face model cache (survives restarts)

Work directory:
- `./work/` - Runner workspace (optional, can be ephemeral)

## Updating

### Update Runner Software

```bash
# Stop container
docker-compose down

# Update RUNNER_VERSION in Dockerfile
# Rebuild
docker-compose build

# Start again (models intact!)
docker-compose up -d
```

### Update Project Code

The GitHub Actions workflow will automatically pull the latest code from the repository on each run.

## Monitoring

### Check Runner Status

```bash
# Check if runner is online
docker-compose ps

# View logs
docker-compose logs -f

# Interactive shell
docker exec -it weirdness-github-runner bash
```

### Verify Models

```bash
ls -lh ./models/transformers/
# Should show downloaded model files
```

## Troubleshooting

### Runner Won't Start

Check logs:
```bash
docker-compose logs github-runner
```

Common issues:
- Invalid RUNNER_TOKEN
- Network connectivity to GitHub
- Already registered runner token

### Models Not Persisting

Ensure volume mount is working:
```bash
docker exec weirdness-github-runner ls -la /app/models
```

### Runner Offline in GitHub

1. Check container is running: `docker-compose ps`
2. Check logs: `docker-compose logs`
3. Re-register runner if needed (delete `./models/.runner` and restart)

## Resource Requirements

- **CPU**: 2+ cores recommended
- **Memory**: 4GB minimum (8GB recommended)
- **Disk**: ~5GB for models and dependencies
- **Network**: Outbound HTTPS to GitHub and Hugging Face

## Security Notes

⚠️ **Important**: 
- Runner has full access to your machine
- Keep RUNNER_TOKEN secret
- Don't expose on public networks without proper security
- Consider firewall rules for additional protection
- Run on isolated infrastructure when possible

## Clean Shutdown

```bash
docker-compose down
```

To fully remove:
```bash
docker-compose down -v  # Also removes volumes
rm -rf models work      # Removes persisted data
```

# Container build test
