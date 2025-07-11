#!/bin/bash

# Build the Docker image
echo "Building Docker image..."
docker build -t contro-bot .

# Run the container
echo "Running container..."
docker run -d \
  --name contro-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -p 5000:5000 \
  contro-bot

echo "Container started! Check logs with: docker logs contro-bot" 