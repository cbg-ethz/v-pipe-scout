#!/bin/bash

# Automatic deployment script for v-pipe-scout
# This script checks for new changes on main branch and deploys them automatically
# Designed to be run via cron job

set -euo pipefail  # Exit on any error, undefined variable, or pipe failure

# Configuration
REPO_DIR="${REPO_DIR:-$(dirname "$(dirname "$(realpath "$0")")")}"  # Default to parent of scripts dir
BRANCH="${BRANCH:-main}"
LOG_FILE="${LOG_FILE:-${REPO_DIR}/deployment.log}"
LOCK_FILE="${LOCK_FILE:-/tmp/v-pipe-scout-deploy.lock}"

# Function to log messages with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Function to clean up lock file on exit
cleanup() {
    rm -f "$LOCK_FILE"
}

# Set up cleanup trap
trap cleanup EXIT

# Check if another deployment is running
if [ -f "$LOCK_FILE" ]; then
    log "ERROR: Another deployment is already running (lock file exists: $LOCK_FILE)"
    exit 1
fi

# Create lock file
echo $$ > "$LOCK_FILE"

log "Starting automatic deployment check"

# Change to repository directory
cd "$REPO_DIR"
log "Working in directory: $(pwd)"

# Fetch the latest changes from remote
log "Fetching latest changes from remote..."
if ! git fetch origin "$BRANCH"; then
    log "ERROR: Failed to fetch from remote"
    exit 1
fi

# Check if we're on the correct branch, if not switch to it
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    log "Currently on branch '$CURRENT_BRANCH', switching to '$BRANCH'..."
    if ! git checkout "$BRANCH"; then
        log "ERROR: Failed to switch to branch '$BRANCH'"
        exit 1
    fi
fi

# Check if there are new commits
LOCAL=$(git rev-parse HEAD)
if ! REMOTE=$(git rev-parse "origin/$BRANCH" 2>/dev/null); then
    log "ERROR: Remote branch 'origin/$BRANCH' not found"
    exit 1
fi

if [ "$LOCAL" = "$REMOTE" ]; then
    log "No new changes detected. Current commit: $LOCAL"
    exit 0
fi

log "New changes detected!"
log "Local commit:  $LOCAL"
log "Remote commit: $REMOTE"

# Pull the latest changes
log "Pulling latest changes..."
if ! git pull origin "$BRANCH"; then
    log "ERROR: Failed to pull changes from remote"
    exit 1
fi

# Get the new commit information
NEW_COMMIT=$(git rev-parse HEAD)
COMMIT_MESSAGE=$(git log -1 --pretty=format:"%s" HEAD)
log "Updated to commit: $NEW_COMMIT"
log "Commit message: $COMMIT_MESSAGE"

# Stop existing services gracefully
log "Stopping existing services..."
if ! docker compose down; then
    log "WARNING: Failed to stop services gracefully, but continuing..."
fi

# Rebuild and start services
log "Building and starting services..."
if ! docker compose up -d --build; then
    log "ERROR: Failed to build and start services"
    
    # Try to restart with the previous version
    log "Attempting to rollback to previous commit..."
    git reset --hard "$LOCAL"
    
    if docker compose up -d --build; then
        log "Successfully rolled back to previous version"
    else
        log "ERROR: Rollback failed! Manual intervention required."
    fi
    exit 1
fi

# Wait a moment for services to start
sleep 10

# Basic health check
log "Performing basic health check..."
if docker compose ps | grep -q "unhealthy\|Exit\|exited"; then
    log "WARNING: Some services appear unhealthy after deployment"
    docker compose ps >> "$LOG_FILE"
else
    log "All services appear to be running normally"
fi

log "Deployment completed successfully!"
log "Services status:"
docker compose ps >> "$LOG_FILE"

log "=========================================="