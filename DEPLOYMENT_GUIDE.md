# Self-Hosted Runner Deployment Guide

## Quick Start

### On Your Deployment Server

```bash
# 1. Clone the repository
git clone https://github.com/rl337/weirdness.git
cd weirdness

# 2. Go to container directory
cd containers/githubaction_summarization

# 3. Get your runner token from GitHub:
#    https://github.com/rl337/weirdness/settings/actions/runners/new

# 4. Configure environment
cp .env.example .env
# Edit .env and add RUNNER_TOKEN

# 5. Deploy
./deploy.sh
```

That's it! The container will:
- Build with all dependencies
- Download and cache models on first run
- Register as a GitHub Actions runner
- Start listening for jobs

## What Gets Created

```
containers/githubaction_summarization/
├── models/              # Persistent model cache (created on deploy)
├── work/                # Runner workspace
└── (container logs)
```

## How It Works

### First Pipeline Run
1. GitHub triggers workflow
2. Self-hosted runner picks up job
3. Downloads transformers model (~1.2GB) to `./models`
4. Processes data and commits results
5. Models saved on host filesystem

### Subsequent Runs
1. GitHub triggers workflow
2. Self-hosted runner picks up job
3. **Models already exist** in `./models`
4. Instant start, no download!
5. Pipeline completes in 30 seconds

## Persistence

Models persist in `./models/` directory on the host machine:
- ✅ Survives container restarts
- ✅ Survives container rebuilds
- ✅ Can backup by copying directory
- ✅ Can delete and re-download if needed

## Monitoring

### View Logs
```bash
cd containers/guckingithubaction_summarization
docker-compose logs -f
```

### Check Runner Status
```bash
docker-compose ps
```

### View in GitHub UI
Go to: https://github.com/rl337/weirdness/settings/actions/runners

## Troubleshooting

### Runner Appears Offline
1. Check container is running: `docker-compose ps`
2. Check logs: `docker-compose logs`
3. Verify network connectivity
4. Re-register if needed (delete `./work/.runner`)

### Models Not Persisting
```bash
# Check volume mount
docker exec weirdness-github-runner ls -la /app/models

# Should show model files from host
```

### Update Container
```bash
docker-compose pull
docker-compose up -d --force-recreate
# Models stay intact!
```

## Resource Requirements

- **CPU**: 2 cores minimum
- **Memory**: 4GB minimum (8GB recommended)
- **Disk**: ~5GB for models + dependencies
- **Network**: Outbound HTTPS to GitHub

## Security

⚠️ Self-hosted runners have access to your machine:
- Run on dedicated/isolated infrastructure
- Use firewall rules
- Keep secrets in GitHub Secrets (not in .env)
- Consider network isolation

