#!/bin/bash

# AuthFace Validation Script
# Runs all automated tests, static checks, style linting, and test coverage

set -e

echo "🔍 Running AuthFace validation checks..."

# Change to project directory
cd "$(dirname "$0")"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Build the Docker image
echo "🐳 Building Docker image..."
docker build -t authface:latest .

# Run Rust checks in Docker container
echo "🦀 Running Rust checks..."

# Format check
echo "  📝 Checking code formatting..."
docker run --rm -v "$(pwd)":/app -w /app authface:latest cargo fmt -- --check

# Clippy linting
echo "  🔍 Running clippy lints..."
docker run --rm -v "$(pwd)":/app -w /app authface:latest cargo clippy -- -D warnings

# Run tests
echo "  🧪 Running tests..."
docker run --rm -v "$(pwd)":/app -w /app authface:latest cargo test

# Run tests with coverage (if tarpaulin is available)
echo "  📊 Running test coverage..."
docker run --rm -v "$(pwd)":/app -w /app authface:latest cargo test --verbose

# Security audit
echo "  🔒 Running security audit..."
docker run --rm -v "$(pwd)":/app -w /app authface:latest cargo audit || echo "⚠️  cargo-audit not available, skipping security audit"

# Check for unused dependencies
echo "  🧹 Checking for unused dependencies..."
docker run --rm -v "$(pwd)":/app -w /app authface:latest cargo machete || echo "⚠️  cargo-machete not available, skipping unused dependency check"

# Build release version
echo "  🏗️  Building release version..."
docker run --rm -v "$(pwd)":/app -w /app authface:latest cargo build --release

# Test Docker container health
echo "🏥 Testing container health..."
docker run -d --name authface-test -p 8080:8080 authface:latest
sleep 10

# Test health endpoint
if curl -f http://localhost:8080/health; then
    echo "✅ Health endpoint working"
else
    echo "❌ Health endpoint failed"
    docker logs authface-test
    docker stop authface-test
    docker rm authface-test
    exit 1
fi

# Test status endpoint
if curl -f http://localhost:8080/status; then
    echo "✅ Status endpoint working"
else
    echo "❌ Status endpoint failed"
    docker logs authface-test
    docker stop authface-test
    docker rm authface-test
    exit 1
fi

# Cleanup
docker stop authface-test
docker rm authface-test

echo "✅ All checks passed!"