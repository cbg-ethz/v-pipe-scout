#!/bin/bash

# V-Pipe Scout Setup Script
# This script helps set up the environment configuration

echo "🚀 V-Pipe Scout Setup"
echo "===================="

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

# Copy example file
echo "📋 Creating .env file from template..."
cp .env.example .env

# Generate a random password
echo "🔐 Generating secure Redis password..."
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Update the .env file
sed -i.bak "s/your_secure_redis_password_here_change_this/$REDIS_PASSWORD/" .env
rm .env.bak 2>/dev/null || true

echo "✅ Environment configuration created!"
echo ""
echo "📝 Configuration summary:"
echo "   - Redis password: [GENERATED]"
echo "   - Config file: .env"
echo ""
echo "🔧 Next steps:"
echo "   1. Review app/config.yaml for LAPIS settings"
echo "   2. Run: docker compose up --build"
echo ""
echo "🔒 Security note: The .env file contains sensitive data and is excluded from git."
