#!/bin/bash
set -e

# Build and push script for weirdness-githubaction container
# Uses rl337/callableapis:base as base image
# Pushes to Docker Hub under rl337/weirdness-githubaction

IMAGE_NAME="rl337/weirdness-githubaction"
VERSION="${1:-latest}"

echo "Building weirdness-githubaction container..."
echo "Version: $VERSION"

# Build from repository root to access project files
cd ../..

# Build the image
docker build \
  -t "$IMAGE_NAME:$VERSION" \
  -t "$IMAGE_NAME:latest" \
  -f containers/githubaction_summarization/Dockerfile \
  .

echo ""
echo "Build complete!"
echo "Tags: $IMAGE_NAME:$VERSION, $IMAGE_NAME:latest"

# Push to Docker Hub
if [ "$1" != "--no-push" ]; then
  echo ""
  echo "Pushing to Docker Hub..."
  docker push "$IMAGE_NAME:$VERSION"
  docker push "$IMAGE_NAME:latest"
  echo "Pushed successfully!"
fi

echo ""
echo "Deploy with:"
echo "  docker pull $IMAGE_NAME:$VERSION"
echo "  docker run -d --name weirdness-runner $IMAGE_NAME:$VERSION"

