# Self-Hosted Runner Setup Guide

## Overview

Self-hosted runners let you run GitHub Actions on your own hardware. This means you can have persistent storage for models!

## How It Works

### Architecture
```
GitHub.com (orchestrator)
    ↓ triggers job
Your self-hosted runner (your machine/server)
    ↓ executes job
Returns results to GitHub
```

### Key Benefits for Your Use Case

1. **Persistent Storage**: Models stay on disk between runs
2. **Custom Hardware**: Use GPUs, fast SSDs, etc.
3. **No Download Overhead**: Models download once, reuse forever
4. **Same Workflow**: Keep using GitHub Actions syntax
5. **Fast Runs**: Should drop from 3-4 minutes to 30 seconds

## Setup Process

### 1. Install Runner Agent

On your machine/server:

```bash
# Download latest runner
cd ~/actions-runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# Extract
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Configure (you'll get token from GitHub UI)
./config.sh --url https://github.com/rl337/weirdness --token YOUR_TOKEN

# Run as service
sudo ./svc.sh install
sudo ./svc.sh start
```

### 2. Configure Workflow to Use Self-Hosted Runner

Update your workflow:

```yaml
jobs:
  build-and-release:
    runs-on: self-hosted  # Instead of ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # ... rest of workflow
```

### 3. Pre-Install Dependencies (One-Time Setup)

On your runner machine:

```bash
# Clone repo
cd /opt/pipeline
git clone https://github.com/rl337/weirdness.git

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Pre-download models
python -c "
from transformers import pipeline
pipeline('summarization', model='sshleifer/distilbart-cnn-12-6')
"
# Models now cached in ~/.cache/huggingface forever
```

## Security Considerations

### Access Control
- Runner has full access to your machine
- Can access all repos you grant it to
- Uses GitHub authentication tokens

### Best Practices
1. **Isolate**: Run on dedicated machine/VM
2. **Network**: Consider firewall rules
3. **Updates**: Keep runner software updated
4. **Secrets**: Use GitHub secrets, never hardcode
5. **Cleanup**: Configure job cleanup after runs

### Labels & Tagging

Use labels to control which jobs run where:

```yaml
jobs:
  build-and-release:
    runs-on: ['self-hosted', 'linux', 'pipeline-server']
```

## Maintenance

### Monitor Status
```bash
# Check runner status
sudo ./svc.sh status

# View logs
tail -f /home/runner/_diag/Runner_*.log
```

### Update Runner
```bash
cd ~/actions-runner
./config.sh remove --token TOKEN
# Download new version
./config.sh --url URL --token NEW_TOKEN
sudo ./svc.sh restart
```

## Cost Comparison

### GitHub Hosted ($0.008/minute)
- 3-4 minute runs × 2/day × 30 days = ~240 minutes/month
- Cost: ~$2/month
- But... no model caching, slow

### Self-Hosted
- Same compute time but on your hardware
- Cost: $0 (if you have spare machine)
- Plus: Fast, persistent cache, full control

## Hybrid Approach

You could use both:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest  # Fast CI checks
    
  build-and-release:
    runs-on: self-hosted    # Deep learning work
```

## Alternative: Using Docker on Self-Hosted Runner

Even better! Bake models into a container:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Download and cache models in image
RUN python -c "from transformers import pipeline; pipeline('summarization', model='sshleifer/distilbart-cnn-12-6')"

COPY . .
```

Then your runner just pulls this image once, and subsequent runs are instant!

