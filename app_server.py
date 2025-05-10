"""
Improved app server with timeouts and performance enhancements
"""
import os
import logging
from gunicorn.app.base import BaseApplication
from gunicorn import util
from main import app

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StandaloneApplication(BaseApplication):
    """Custom Gunicorn application for improved performance and reliability"""
    
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

if __name__ == '__main__':
    logger.info("Starting application with enhanced server configuration")
    
    # Enhanced server options for better stability and performance
    options = {
        'bind': '0.0.0.0:5000',
        'workers': 2,  # Use 2 worker processes for better handling of requests
        'worker_class': 'sync',
        'timeout': 120,  # Increased timeout to 120 seconds
        'keepalive': 5,  # Keep-alive connections for 5 seconds
        'max_requests': 1000,  # Restart workers after 1000 requests to prevent memory leaks
        'max_requests_jitter': 50,  # Add randomness to max_requests to prevent all workers restarting at once
        'reload': True,  # Auto-reload on code changes
        'preload_app': False,  # Don't preload app to ensure clean restarts
        'accesslog': '-',  # Log to stdout
        'errorlog': '-',  # Log errors to stdout
        'loglevel': 'info'
    }
    
    logger.info(f"Server configuration: {options}")
    StandaloneApplication(app, options).run()