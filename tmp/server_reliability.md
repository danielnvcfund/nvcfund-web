# Server Reliability Enhancement Guide

This document explains the various improvements implemented to enhance the reliability of the NVC Banking Platform and reduce timeout issues.

## Healthcheck Endpoints

We've added several healthcheck endpoints to monitor the application health:

- **/ping**: Simple endpoint that always returns a 200 response with a timestamp.
- **/health/**: Basic healthcheck with application uptime.
- **/health/ready**: Readiness probe that checks database connectivity.
- **/health/system**: Detailed system status including memory usage and database information.

These endpoints can be used by monitoring tools to ensure the application is running correctly.

## Error Handling

### Custom Error Pages

Custom error pages have been created for common HTTP errors:

- **504 Gateway Timeout**: A user-friendly page that explains the issue and provides guidance.

### Request Monitoring

The application now monitors request processing time and logs warnings for slow requests:

```python
@app.before_request
def start_timer():
    # Record request start time
    g.start_time = time.time()
    
@app.after_request
def log_request_time(response):
    # Calculate and log request time
    elapsed = time.time() - g.start_time
    # Log warnings for slow requests (>5s)
    if elapsed > 5.0:
        logger.warning(f"Slow request detected: {request.method} {request.path}")
    return response
```

## Server Configuration

### Improved Gunicorn Settings

The Gunicorn server has been configured for better stability:

- **Workers**: 2 worker processes for better request handling
- **Timeout**: Increased to 120 seconds to handle complex operations
- **Keep-alive**: Set to 5 seconds to maintain persistent connections
- **Max Requests**: Workers are automatically restarted after 1000 requests to prevent memory leaks
- **Max Requests Jitter**: Added 50 request jitter to prevent all workers restarting simultaneously

### Enhanced Start Script

A custom start script (`start_server.sh`) has been created with:

- Database connection validation before startup
- Proper error logging
- Advanced Gunicorn configuration

## Monitoring and Recovery

### Application Monitor

A monitoring script (`monitor.py`) has been implemented to:

- Periodically check application health
- Automatically restart the application if it's not responding
- Log health status and restart attempts

To use the monitor:

```bash
# Start the monitor in the background
python monitor.py &
```

### Graceful Shutdown

Signal handlers have been added for graceful shutdown:

```python
def handle_sigterm(signum, frame):
    """Handle SIGTERM signal - log and exit gracefully"""
    logger.info("Received SIGTERM. Shutting down gracefully...")
    sys.exit(0)
```

## Best Practices for Maintaining Reliability

1. **Use Healthcheck Endpoints**: Regularly check the healthcheck endpoints to monitor application status.
2. **Monitor Logs**: Watch for "Slow request detected" warnings to identify performance bottlenecks.
3. **Run the Monitor Script**: Use the monitor script for production deployments to ensure automatic recovery.
4. **Database Connection Pooling**: The application uses connection pooling to improve database reliability.
5. **Regular Maintenance**: Periodically restart the application to ensure memory is freed and resources are reset.
6. **Check System Status**: Use the `/health/system` endpoint to monitor memory usage and overall system health.
7. **Use Custom Start Script**: Use the `start_server.sh` script for production deployments instead of direct Gunicorn commands.

## Troubleshooting Common Issues

### Application Timeouts

If you encounter gateway timeouts:

1. Check if the application is running (`curl http://localhost:5000/ping`)
2. Check database connectivity (`curl http://localhost:5000/health/ready`)
3. Look for slow requests in the logs (`grep "Slow request" logs/*.log`)
4. Restart the application using the workflow (`replit workflow restart "Start application"`)

### Memory Issues

If the application becomes slow or unresponsive:

1. Check memory usage (`curl http://localhost:5000/health/system`)
2. Restart the application to free memory
3. Consider increasing worker count for high-traffic scenarios