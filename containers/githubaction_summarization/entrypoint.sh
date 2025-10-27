#!/bin/bash
set -e

# Start API server in background
echo "Starting health check API server..."
cd /app/api
python3 api-server.py &
API_PID=$!

# Check if runner is configured
if [ ! -f "/runner/.runner" ]; then
  echo "Runner not configured. Running setup..."
  /runner/setup-runner.sh
fi

# Function to cleanup on exit
cleanup() {
  echo "Shutting down..."
  kill $API_PID 2>/dev/null || true
  exit 0
}
trap cleanup SIGTERM SIGINT

# Start the runner
echo "Starting GitHub Actions Runner..."
cd /runner
./run.sh

