"""
Optimized Gunicorn configuration for NVC Banking Platform
This configuration addresses memory usage and timeout issues
"""

import os
import multiprocessing

# Server socket binding
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 1  # Use a single worker to avoid excessive memory usage
threads = 4  # Multiple threads for concurrent requests
worker_class = "gthread"  # Use threads for concurrent workers
worker_connections = 1000  # Maximum number of connections for each worker

# Timeouts
timeout = 120  # Increase timeout to prevent premature worker restarts
graceful_timeout = 10  # Graceful worker restart timeout
keepalive = 5  # How long to wait for requests on a Keep-Alive connection

# Performance optimizations
max_requests = 100  # Restart workers after handling this many requests
max_requests_jitter = 10  # Add randomness to prevent all workers restarting at once
limit_request_line = 4096  # Limit size of HTTP request line
limit_request_fields = 100  # Limit number of HTTP headers
limit_request_field_size = 8190  # Limit size of HTTP headers

# Logging
loglevel = "warning"  # Log level (debug, info, warning, error, critical)
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "nvc_banking_platform"
default_proc_name = "nvc_banking_platform"

# Debugging and development
reload = True  # Auto-reload when code changes
reload_engine = "poll"  # Method to detect code changes
check_config = True  # Check config before starting
spew = False  # Install a trace function that spews every executed line

# Production settings
daemon = False  # Don't daemonize the process
raw_env = ["FLASK_ENV=production"]  # Environment variables to pass

# Preload app to save memory
preload_app = True

# Execute this function when worker starts
def on_starting(server):
    """Log when the server starts"""
    print("Starting optimized gunicorn server for NVC Banking Platform")

def post_fork(server, worker):
    """Customize worker after fork"""
    # Import and run the performance optimization script
    try:
        from optimize_performance import optimize_all
        optimize_all()
    except ImportError:
        print("Failed to import performance optimization module")