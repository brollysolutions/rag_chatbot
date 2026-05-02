#!/bin/bash

echo "Starting deployment..."

# 1. Stop existing containers (optional, but good for clean deployments)
docker-compose down

# 2. Rebuild and start the containers in the background
echo "Rebuilding and starting Docker containers..."
docker-compose up -d --build

echo "Deployment complete! Uvicorn is now running in the background."

# 3. Document Upload (Commented out by default)
docker exec brolly_rag_bot python run_upload.py
echo "Documents uploaded to Qdrant."

