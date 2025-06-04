# Automatic Deployment Setup

This document describes how to set up automatic deployment for v-pipe-scout using the provided deployment script.

## Overview

The automatic deployment system checks for new changes on the main branch every few minutes and automatically deploys them if found. This eliminates the need to manually run:

```bash
cd ../../local0/repos/v-pipe-scout
git pull
docker-compose up -d --build
```

## Setup Instructions

### 1. Deployment Script

The deployment script is located at `scripts/auto-deploy.sh`. It automatically:

- Fetches latest changes from the remote repository
- Compares local and remote commit hashes
- Pulls changes if new commits are available
- Rebuilds and restarts Docker Compose services
- Logs all activities with timestamps
- Includes basic rollback capability on deployment failure

### 2. Cron Job Setup

To run the deployment check every 5 minutes, add the following to your crontab:

```bash
# Edit crontab
crontab -e

# Add this line (adjust paths as needed):
*/5 * * * * /local0/repos/v-pipe-scout/scripts/auto-deploy.sh >/dev/null 2>&1
```

For different check intervals:
- Every 2 minutes: `*/2 * * * *`
- Every 10 minutes: `*/10 * * * *`
- Every hour: `0 * * * *`

### 3. Configuration

The script accepts several environment variables for configuration:

```bash
# Repository directory (default: auto-detected)
export REPO_DIR="/local0/repos/v-pipe-scout"

# Git branch to track (default: main)
export BRANCH="main"

# Log file location (default: deployment.log in repo root)
export LOG_FILE="/var/log/v-pipe-scout-deployment.log"
```

### 4. Custom Configuration Example

For a custom setup, create a wrapper script:

```bash
#!/bin/bash
# /local0/scripts/v-pipe-scout-deploy.sh

export REPO_DIR="/local0/repos/v-pipe-scout"
export LOG_FILE="/var/log/v-pipe-scout-deployment.log"

cd "$REPO_DIR"
./scripts/auto-deploy.sh
```

Then use this wrapper in your crontab:

```bash
*/5 * * * * /local0/scripts/v-pipe-scout-deploy.sh >/dev/null 2>&1
```

## Monitoring

### Log File

The deployment script creates detailed logs at `deployment.log` (or your custom location). Monitor this file to track deployment activities:

```bash
# View recent deployments
tail -f /local0/repos/v-pipe-scout/deployment.log

# Check for any deployment errors
grep ERROR /local0/repos/v-pipe-scout/deployment.log
```

### Service Status

Check if services are running properly:

```bash
cd /local0/repos/v-pipe-scout
docker compose ps
docker compose logs
```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the script is executable:
   ```bash
   chmod +x /local0/repos/v-pipe-scout/scripts/auto-deploy.sh
   ```

2. **Docker Permission Issues**: Ensure your user can run Docker commands:
   ```bash
   sudo usermod -aG docker $USER
   # Log out and back in for changes to take effect
   ```

3. **Git Authentication**: If using HTTPS, ensure credentials are cached:
   ```bash
   git config --global credential.helper store
   # Or use SSH keys for authentication
   ```

4. **Lock File Issues**: If deployment gets stuck, remove the lock file:
   ```bash
   rm -f /tmp/v-pipe-scout-deploy.lock
   ```

### Manual Deployment

If automatic deployment fails, you can still deploy manually:

```bash
cd /local0/repos/v-pipe-scout
git pull
docker compose down
docker compose up -d --build
```

### Rollback

The script includes automatic rollback on deployment failure. For manual rollback:

```bash
cd /local0/repos/v-pipe-scout
git log --oneline -5  # Find the commit to rollback to
git reset --hard <commit-hash>
docker compose down
docker compose up -d --build
```

## Security Considerations

- The script runs with the privileges of the user account
- Ensure the repository directory has appropriate permissions
- Consider running in a dedicated user account for better isolation
- Monitor log files for any suspicious activity

## Testing

Test the deployment script manually before setting up cron:

```bash
cd /local0/repos/v-pipe-scout
./scripts/auto-deploy.sh
```

Check the log output and verify services are running correctly.