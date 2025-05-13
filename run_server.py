#!/usr/bin/env python3
"""
Optimized server runner for NVC Banking Platform
This script starts gunicorn with optimized settings to prevent timeouts and memory issues
"""

import os
import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ServerRunner")

def run_server():
    """Run the optimized gunicorn server"""
    logger.info("Starting optimized gunicorn server...")
    
    # Define optimized parameters
    bind_address = "0.0.0.0:5000"
    timeout = 120  # Increased timeout to prevent worker restarts
    workers = 1    # Single worker to prevent memory issues
    threads = 4    # Multiple threads for concurrent requests
    max_requests = 100  # Restart workers after handling this many requests
    max_requests_jitter = 10  # Add randomness to prevent all workers restarting at once
    
    # Command to run optimized gunicorn
    cmd = [
        "gunicorn",
        f"--bind={bind_address}",
        "--reuse-port",
        "--reload",
        f"--timeout={timeout}",
        f"--workers={workers}",
        f"--threads={threads}",
        f"--max-requests={max_requests}",
        f"--max-requests-jitter={max_requests_jitter}",
        "--log-level=info",
        "--access-logfile=-",
        "--error-logfile=-",
        "main:app"
    ]
    
    # Log the command being executed
    logger.info(f"Executing command: {' '.join(cmd)}")
    
    try:
        # Execute gunicorn with the optimized parameters
        process = subprocess.Popen(cmd)
        logger.info(f"Server started with PID: {process.pid}")
        # Wait for the process to complete
        process.wait()
    except KeyboardInterrupt:
        logger.info("Server shutting down due to keyboard interrupt")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_server()