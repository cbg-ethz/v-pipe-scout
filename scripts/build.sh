#!/bin/bash

# Build script for v-pipe-scout with version information
# Usage: ./scripts/build.sh [tag]

set -e

# Get git information
BUILD_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
BUILD_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# If a tag is provided as argument, use it
if [ -n "$1" ]; then
    BUILD_TAG="$1"
fi

echo "Building v-pipe-scout with version information:"
echo "  Commit: $BUILD_COMMIT"
echo "  Tag: ${BUILD_TAG:-<none>}"
echo "  Build Date: $BUILD_DATE"
echo

# Export environment variables for docker-compose
export BUILD_COMMIT
export BUILD_TAG  
export BUILD_DATE

# Build with docker-compose
docker-compose build --no-cache streamlit

echo
echo "Build completed successfully!"
echo "To run: docker-compose up"
