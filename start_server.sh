#!/bin/bash

# Enhanced startup script for more reliable application operation
# This script adds improved logging and monitoring for the Gunicorn server

echo "Starting NVC Banking Platform with enhanced monitoring..."

# Make the script executable
chmod +x start_server.sh

# Set important environment variables
export GUNICORN_CMD_ARGS="--bind=0.0.0.0:5000 --workers=2 --timeout=120 --keep-alive=5 --max-requests=1000 --max-requests-jitter=50 --log-level=info --access-logfile=- --error-logfile=- --capture-output"

echo "Server configuration:"
echo "- Binding to: 0.0.0.0:5000"
echo "- Workers: 2"
echo "- Timeout: 120 seconds"
echo "- Keep-alive: 5 seconds" 
echo "- Max requests per worker: 1000 (with jitter: 50)"

# Create error log directory if it doesn't exist
mkdir -p logs

# Check if database is accessible
echo "Checking database connection..."
python -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ.get('DATABASE_URL'))
with engine.connect() as connection:
    result = connection.execute(text('SELECT 1'))
    print('Database connection successful:', result.scalar())
" || { echo "Error: Database connection failed"; exit 1; }

# Start Gunicorn with advanced configuration
echo "Starting Gunicorn server with improved reliability settings..."
exec gunicorn main:app