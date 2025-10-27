#!/bin/bash
set -e

# Deployment script for GitHub Actions self-hosted runner
echo "Deploying GitHub Actions Self-Hosted Runner..."

# Check if .env exists
if [ ! -f .env ]; then
  echo "ERROR: .env file not found!"
  echo "Please copy .env.example to .env and configure it:"
  echo "  cp .env.example .env"
  exit 1
fi

# Load environment variables
source .env

# Check if RUNNER_TOKEN is set
if [ -z "$RUNNER_TOKEN" ]; then
  echo "ERROR: RUNNER_TOKEN not set in .env file"
  echo "Get token from: https://github.com/rl337/weirdness/settings/actions/runners/new"
  exit 1
fi

# Create directories
echo "Creating directories..."
mkdir -p models work
chmod 755 models work

# Build image
echo "Building Docker image..."
docker-compose build

# Stop existing container if running
echo "Stopping existing container if running..."
docker-compose down || true

# Start container
echo "Starting GitHub Actions runner..."
docker-compose up -d

# Show logs
echo ""
echo "Container started! Showing logs (Ctrl+C to exit)..."
echo "Container name: weirdness-github-runner"
echo ""
docker-compose logs -f github-runner

