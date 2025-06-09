#!/bin/bash

# Set the number of runs
NUM_RUNS=1

LOG_DIR="phaser/server/logs/docker"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Run the Docker Compose stack NUM_RUNS times sequentially
for i in $(seq 1 $NUM_RUNS)
do
    echo "===== Starting run $i of $NUM_RUNS ====="
    
    # Stop any existing containers
    docker compose down

    # Prune all containers
    docker container prune -f

    # Prune all volumes
    docker volume prune -f
    
    # Start containers and wait for them to exit
    docker compose up --abort-on-container-exit
    
    echo "===== Completed run $i of $NUM_RUNS ====="
    
    # Create timestamp for log file in ISO 8601 format with milliseconds
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    
    # Save logs from all containers
    echo "Saving container logs..."
    docker compose logs > "$LOG_DIR/docker_logs_$TIMESTAMP.txt"
    echo "Logs saved to $LOG_DIR/docker_logs_$TIMESTAMP.txt"
    
    # Small delay between runs
    if [ $i -lt $NUM_RUNS ]; then
        echo "Waiting 5 seconds before next run..."
        sleep 5
    fi
done

echo "All $NUM_RUNS runs completed."