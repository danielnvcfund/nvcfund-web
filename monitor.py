#!/usr/bin/env python3
"""
Application Monitor Script
Periodically pings the application and restarts it if it's not responding
"""
import os
import time
import logging
import subprocess
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app_monitor")

# Configuration
HEALTH_CHECK_URL = "http://localhost:5000/ping"
CHECK_INTERVAL = 30  # seconds
MAX_FAILURES = 3
WORKFLOW_NAME = "Start application"
RESTART_COMMAND = ["replit", "workflow", "restart", WORKFLOW_NAME]

def check_app_health():
    """Check if the application is responding to health checks"""
    try:
        response = requests.get(HEALTH_CHECK_URL, timeout=5)
        if response.status_code == 200:
            logger.debug(f"Health check successful: {response.json()}")
            return True
        else:
            logger.warning(f"Health check failed with status code: {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"Health check request failed: {str(e)}")
        return False

def restart_app():
    """Restart the application workflow"""
    logger.info(f"Attempting to restart workflow: {WORKFLOW_NAME}")
    try:
        result = subprocess.run(RESTART_COMMAND, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Successfully restarted workflow: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"Failed to restart workflow: {result.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"Error restarting workflow: {str(e)}")
        return False

def main():
    """Main monitoring loop"""
    logger.info("Starting application monitor")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    failures = 0
    
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.debug(f"Checking application health at {timestamp}")
        
        if check_app_health():
            failures = 0
            logger.debug("Application is healthy")
        else:
            failures += 1
            logger.warning(f"Application health check failed. Consecutive failures: {failures}/{MAX_FAILURES}")
            
            if failures >= MAX_FAILURES:
                logger.error(f"Application has failed {failures} consecutive health checks. Restarting...")
                restart_success = restart_app()
                if restart_success:
                    failures = 0
                    # Wait a bit longer after restart to give the app time to initialize
                    time.sleep(CHECK_INTERVAL * 2)
                    continue
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.critical(f"Unhandled exception in monitor: {str(e)}", exc_info=True)