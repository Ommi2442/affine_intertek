#!/bin/bash

# Entrypoint script to handle both container services

if [ "$CONTAINER_TYPE" = "queue_worker" ]; then
    echo "Starting Queue Worker on port 9000..."
    python queue_worker.py
else
    echo "Starting FastAPI on port 8000..."
    uvicorn main:app --host 0.0.0.0 --port 8000
fi