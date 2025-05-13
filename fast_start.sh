#!/bin/bash
# Fast start script with performance optimizations

# Function to log with timestamp
log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Stop any running gunicorn processes
stop_existing() {
  log "Stopping any existing gunicorn processes..."
  pkill -f gunicorn || true
  sleep 1
}

# Apply performance optimizations
apply_optimizations() {
  log "Applying performance optimizations..."
  python optimize_performance.py
}

# Start optimized gunicorn with the main app
start_optimized_server() {
  log "Starting optimized server..."
  
  # Set environment variables
  export FLASK_ENV=production
  export PYTHONOPTIMIZE=1
  
  # Define optimized parameters
  BIND_ADDRESS="0.0.0.0:5000"
  TIMEOUT=120
  WORKERS=1
  THREADS=4
  MAX_REQUESTS=100
  MAX_REQUESTS_JITTER=10
  
  # Start gunicorn with optimized settings
  exec gunicorn \
    --bind=$BIND_ADDRESS \
    --reuse-port \
    --reload \
    --timeout=$TIMEOUT \
    --workers=$WORKERS \
    --threads=$THREADS \
    --max-requests=$MAX_REQUESTS \
    --max-requests-jitter=$MAX_REQUESTS_JITTER \
    --log-level=warning \
    --access-logfile=- \
    --error-logfile=- \
    main:app
}

# Main execution
log "Starting fast startup sequence..."
stop_existing
apply_optimizations
start_optimized_server