#!/bin/bash
set -e

# Check if runner is configured
if [ ! -f "/runner/.runner" ]; then
  echo "Runner not configured. Running setup..."
  /runner/setup-runner.sh
fi

# Start the runner
echo "Starting GitHub Actions Runner..."
cd /runner
exec ./run.sh

