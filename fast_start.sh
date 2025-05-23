#!/bin/bash
# Performance-optimized server startup script
# This script starts the NVC Banking Platform with performance optimizations

# Display startup message
echo "Starting NVC Banking Platform with performance optimizations..."

# Apply runtime optimizations
python optimize_performance.py

# Kill any existing gunicorn processes
pkill -f gunicorn || true

# Wait for processes to terminate
sleep 1

# Start optimized server
echo "Starting optimized gunicorn server..."
gunicorn -c optimized_gunicorn.conf.py main:app --bind 0.0.0.0:5000 --timeout 120