#!/bin/bash

# Build the agent image
echo "Building avalon-agent image..."
docker build -t avalon-agent -f ./agent/Dockerfile.agent ./agent

# Create a network if it doesn't exist
echo "Creating network if it doesn't exist..."
docker network create avalon-network 2>/dev/null || true

# Check if the container already exists and remove it
echo "Checking for existing servant-1 container..."
if [ "$(docker ps -a -q -f name=servant-1)" ]; then
  echo "Removing existing servant-1 container..."
  docker stop servant-1 2>/dev/null || true
  docker rm servant-1 2>/dev/null || true
fi

# Run the servant-1 agent
echo "Starting servant-1 agent container..."
docker run -d \
  --name servant-1 \
  --network avalon-network \
  --hostname servant1 \
  -p 23009:23009 \
  -v "$(pwd)/agent:/app" \
  -v "$(pwd)/config.json:/app/config.json" \
  --env-file .env \
  -e ROLE="servant-1" \
  -e FASTAPI_PORT="23009" \
  avalon-agent

echo "Container started! (Hopefully)"
echo "Reach the agent API at http://127.0.0.1:23009/docs (you can also test the API there)"
echo "You can keep track of the agent logs with 'docker logs -f servant-1'"
echo "When you are done, you can stop the container with 'docker stop servant-1'"