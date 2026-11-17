#!/usr/bin/env bash
# Production Deployment Script for India-region VM (Ubuntu 22.04 / 24.04 LTS)
# Target Regions: AWS ap-south-1 (Mumbai) or GCP asia-south1 (Delhi)
set -euo pipefail

echo "=========================================================="
echo "WeatherGPT Production VM Deployment Script"
echo "=========================================================="

# 1. Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed on this VM."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "Error: Docker Compose v2 is not installed."
    exit 1
fi

# 2. Check for .env.production file
if [ ! -f .env.production ]; then
    echo "Error: .env.production file not found."
    echo "Please copy deploy/ENV_CHECKLIST.md, populate secrets, and create .env.production."
    exit 1
fi

echo "--> Pulling latest production container images..."
docker compose -f deploy/compose.prod.yaml pull

echo "--> Applying database migrations..."
docker compose -f deploy/compose.prod.yaml run --rm api python -m alembic upgrade head

echo "--> Launching production stack with Caddy automatic TLS..."
docker compose -f deploy/compose.prod.yaml up -d

echo "--> Verifying health check..."
sleep 5
curl -fsS http://localhost:8000/healthz || {
    echo "Health check failed!"
    docker compose -f deploy/compose.prod.yaml logs api
    exit 1
}

echo "=========================================================="
echo "Deployment Successful!"
echo "Site is live at https://weathergpt.in"
echo "=========================================================="
