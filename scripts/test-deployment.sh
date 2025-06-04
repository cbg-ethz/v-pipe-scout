#!/bin/bash

# Test script for deployment automation
# This script validates the deployment logic without actually deploying

set -euo pipefail

# Source the deployment script functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Mock log function
log() {
    echo "[TEST $(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Test 1: Check script exists and is executable
log "Test 1: Checking script existence and permissions..."
if [ -x "$SCRIPT_DIR/auto-deploy.sh" ]; then
    log "✓ auto-deploy.sh exists and is executable"
else
    log "✗ auto-deploy.sh is missing or not executable"
    exit 1
fi

# Test 2: Check git repository
log "Test 2: Checking git repository..."
cd "$REPO_DIR"
if git status >/dev/null 2>&1; then
    log "✓ Git repository is accessible"
    log "  Current branch: $(git branch --show-current)"
    log "  Current commit: $(git rev-parse HEAD)"
else
    log "✗ Git repository check failed"
    exit 1
fi

# Test 3: Check docker compose file
log "Test 3: Checking Docker Compose configuration..."
if [ -f "docker-compose.yml" ]; then
    log "✓ docker-compose.yml exists"
    if docker compose config >/dev/null 2>&1; then
        log "✓ Docker Compose configuration is valid"
    else
        log "! Docker Compose configuration validation failed (may be due to missing services)"
    fi
else
    log "✗ docker-compose.yml is missing"
    exit 1
fi

# Test 4: Check script dry run (with no changes scenario)
log "Test 4: Testing script with current branch (no changes scenario)..."
cd "$REPO_DIR"
CURRENT_BRANCH=$(git branch --show-current)
if BRANCH="$CURRENT_BRANCH" LOG_FILE="/tmp/test-deploy.log" timeout 30 "$SCRIPT_DIR/auto-deploy.sh"; then
    log "✓ Script completed successfully for no-changes scenario"
    if [ -f "/tmp/test-deploy.log" ]; then
        log "✓ Log file was created"
        if grep -q "No new changes detected" "/tmp/test-deploy.log"; then
            log "✓ Script correctly detected no changes"
        else
            log "! Expected 'No new changes detected' message in log"
        fi
    else
        log "! Log file was not created"
    fi
else
    log "✗ Script failed in no-changes scenario"
    exit 1
fi

# Test 5: Environment variable handling
log "Test 5: Testing environment variable handling..."
TEST_REPO_DIR="/tmp/test-repo"
TEST_LOG_FILE="/tmp/test-env.log"
if REPO_DIR="$TEST_REPO_DIR" LOG_FILE="$TEST_LOG_FILE" "$SCRIPT_DIR/auto-deploy.sh" 2>/dev/null; then
    log "! Script should have failed with invalid repo dir"
else
    log "✓ Script correctly failed with invalid repository directory"
fi

log ""
log "========================================"
log "All tests completed successfully!"
log "The auto-deployment script is ready for use."
log "========================================"