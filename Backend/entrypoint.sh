#!/bin/bash

# Entrypoint script to handle both container services

if [ "$CONTAINER_TYPE" = "queue_worker" ]; then
    echo "Starting TRF Worker (FastAPI) on port 9000..."
    uvicorn worker_main:app \
        --host 0.0.0.0 \
        --port 9000 \
        --workers 4 \
        --timeout-keep-alive 120
else
    echo "Starting FastAPI API on port 8000..."
    uvicorn main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --timeout-keep-alive 120
fi
