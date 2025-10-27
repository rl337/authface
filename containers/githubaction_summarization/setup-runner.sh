#!/bin/bash
set -e

RUNNER_VERSION="2.311.0"
GITHUB_URL="${GITHUB_REPO}"
RUNNER_TOKEN="${RUNNER_TOKEN}"

echo "Setting up GitHub Actions Runner ${RUNNER_VERSION}..."

# Download runner
if [ ! -f "actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" ]; then
  echo "Downloading runner..."
  curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz \
    -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
fi

# Extract
if [ ! -d "bin" ]; then
  echo "Extracting runner..."
  tar xzf ./actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
fi

# Install dependencies (use our built dependencies since we're in Alpine)
echo "Installing runner dependencies..."
./bin/installdependencies.sh || echo "Dependencies already installed or failed"

# Configure runner
if [ ! -f ".runner" ]; then
  echo "Configuring runner for ${GITHUB_URL}..."
  ./config.sh --url "${GITHUB_URL}" --token "${RUNNER_TOKEN}" --name "weirdness-githubaction-runner" --work "_work" --replace
fi

echo "Runner setup complete!"

