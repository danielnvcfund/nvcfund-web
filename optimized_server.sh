#!/bin/bash
# Optimized server script
echo "Starting optimized gunicorn server..."

# Clean up any existing gunicorn processes
pkill -f gunicorn || true

# Define optimized parameters
BIND_ADDRESS="0.0.0.0:5000"
TIMEOUT=120       # Increased timeout to prevent worker restarts
WORKERS=1         # Single worker to prevent memory issues
THREADS=4         # Multiple threads for concurrent requests
MAX_REQUESTS=100  # Restart workers after handling this many requests
MAX_REQUESTS_JITTER=10  # Add randomness to prevent all workers restarting at once

# Run gunicorn with optimized settings
exec gunicorn \
  --bind=$BIND_ADDRESS \
  --reuse-port \
  --reload \
  --timeout=$TIMEOUT \
  --workers=$WORKERS \
  --threads=$THREADS \
  --max-requests=$MAX_REQUESTS \
  --max-requests-jitter=$MAX_REQUESTS_JITTER \
  --log-level=info \
  --access-logfile=- \
  --error-logfile=- \
  main:app