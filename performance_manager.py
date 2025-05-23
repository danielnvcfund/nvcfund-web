#!/usr/bin/env python3
"""
Performance Manager for NVC Banking Platform

This script provides an easy way to apply performance optimizations to
the NVC Banking Platform. It can be run independently to:

1. Add database indices for faster queries
2. Optimize server configurations
3. Clear caches and reduce memory usage
4. Apply template and static file optimizations
5. Check for and resolve common performance bottlenecks
"""

import os
import sys
import time
import argparse
import logging
import importlib
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PerformanceManager")

class PerformanceManager:
    """Manage performance optimizations for NVC Banking Platform"""
    
    def __init__(self):
        """Initialize performance manager"""
        self.results = {}
        self.available_optimizations = [
            "database",     # Database optimizations
            "memory",       # Memory usage optimization
            "server",       # Server configuration optimization
            "cache",        # Cache optimization
            "templates",    # Template rendering optimization
            "static",       # Static file handling
            "blockchain",   # Blockchain interaction optimization
            "logging"       # Logging optimization
        ]
        
    def optimize_database(self):
        """Apply database optimizations"""
        logger.info("Applying database optimizations...")
        
        try:
            # Import and run the database optimizer
            from db_optimize_direct import optimize_database
            results = optimize_database()
            logger.info("Database optimization complete")
            return results
        except ImportError:
            logger.error("Database optimizer not found. Creating one...")
            
            # Create a simple database optimizer function
            try:
                import psycopg2
                from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
                
                # Get database connection
                db_url = os.environ.get("DATABASE_URL")
                if not db_url:
                    logger.error("DATABASE_URL environment variable not set")
                    return {"status": "error", "message": "DATABASE_URL not set"}
                    
                conn = psycopg2.connect(db_url)
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                
                # Simple optimization: add indices to common fields
                with conn.cursor() as cursor:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON \"user\" (email);")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_username ON \"user\" (username);")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transaction_user_id ON transaction (user_id);")
                    cursor.execute("ANALYZE;")
                
                conn.close()
                logger.info("Applied basic database optimizations")
                
                return {"status": "success", "indices_added": 3}
            except Exception as e:
                logger.error(f"Error applying database optimizations: {str(e)}")
                return {"status": "error", "message": str(e)}
            
    def optimize_memory(self):
        """Optimize memory usage"""
        logger.info("Optimizing memory usage...")
        
        try:
            # Import and run the memory optimizer
            from optimize_performance import optimize_memory_usage
            optimize_memory_usage()
            
            # Additional memory cleanup
            import gc
            collected = gc.collect()
            logger.info(f"Garbage collection freed {collected} objects")
            
            return {"status": "success", "objects_collected": collected}
        except ImportError:
            logger.warning("Memory optimizer not found, using basic optimization")
            
            # Basic memory optimization
            import gc
            collected = gc.collect()
            logger.info(f"Garbage collection freed {collected} objects")
            
            return {"status": "success", "objects_collected": collected}
            
    def optimize_server(self):
        """Optimize server configuration"""
        logger.info("Optimizing server configuration...")
        
        # Check if optimized configuration exists
        config_path = "optimized_gunicorn.conf.py"
        if not os.path.exists(config_path):
            logger.error(f"Optimized server configuration not found at: {config_path}")
            return {"status": "error", "message": "Configuration file not found"}
            
        # Create or update startup script
        startup_script = "fast_start.sh"
        if not os.path.exists(startup_script):
            # Create startup script
            with open(startup_script, "w") as f:
                f.write("""#!/bin/bash
# Performance-optimized server startup script
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
""")
            
            # Make it executable
            os.chmod(startup_script, 0o755)
            logger.info(f"Created optimized startup script: {startup_script}")
        
        return {"status": "success", "script": startup_script, "config": config_path}
        
    def optimize_cache(self):
        """Optimize caching"""
        logger.info("Optimizing cache settings...")
        
        try:
            # Import and run the cache optimizer
            from optimize_performance import replace_memory_cache
            replace_memory_cache()
            
            # Check if fast_memory_cache exists
            cache_module = "fast_memory_cache.py"
            if not os.path.exists(cache_module):
                logger.warning(f"Fast memory cache module not found: {cache_module}")
                return {"status": "warning", "message": "Cache module not found"}
                
            return {"status": "success", "cache_module": cache_module}
        except ImportError:
            logger.warning("Cache optimizer not found")
            return {"status": "warning", "message": "Cache optimizer not found"}
            
    def optimize_templates(self):
        """Optimize template rendering"""
        logger.info("Optimizing template rendering...")
        
        try:
            # Import and run the template optimizer
            from optimize_performance import optimize_template_engine
            optimize_template_engine()
            
            return {"status": "success"}
        except ImportError:
            logger.warning("Template optimizer not found")
            return {"status": "warning", "message": "Template optimizer not found"}
            
    def optimize_static(self):
        """Optimize static file handling"""
        logger.info("Optimizing static file handling...")
        
        try:
            # Import and run the asset optimizer
            from optimize_performance import optimize_asset_loading
            optimize_asset_loading()
            
            return {"status": "success"}
        except ImportError:
            logger.warning("Asset optimizer not found")
            return {"status": "warning", "message": "Asset optimizer not found"}
            
    def optimize_blockchain(self):
        """Optimize blockchain interaction"""
        logger.info("Optimizing blockchain interaction...")
        
        # Basic optimization: set cache expiry for blockchain connections
        try:
            # Check if cache utils exists
            cache_module = "cache_utils.py"
            if not os.path.exists(cache_module):
                logger.warning(f"Cache utils module not found: {cache_module}")
                return {"status": "warning", "message": "Cache utils module not found"}
                
            # Set blockchain cache expiry to 5 minutes
            with open(cache_module, "r") as f:
                content = f.read()
                
            if "WEB3_CACHE_EXPIRY" in content:
                # Already optimized
                logger.info("Blockchain cache already optimized")
            else:
                # Add cache expiry setting
                with open(cache_module, "a") as f:
                    f.write("\n\n# Blockchain connection cache expiry (5 minutes)\nWEB3_CACHE_EXPIRY = 300  # seconds\n")
                logger.info("Added blockchain cache expiry setting")
                
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error optimizing blockchain interaction: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    def optimize_logging(self):
        """Optimize logging configuration"""
        logger.info("Optimizing logging configuration...")
        
        try:
            # Import and run the logging optimizer
            from optimize_performance import disable_excessive_logging
            disable_excessive_logging()
            
            return {"status": "success"}
        except ImportError:
            logger.warning("Logging optimizer not found, applying basic optimization")
            
            # Basic logging optimization
            for module in ['werkzeug', 'sqlalchemy.engine', 'urllib3', 'blockchain', 'web3', 'pyppdf']:
                logging.getLogger(module).setLevel(logging.WARNING)
                
            logger.info("Applied basic logging optimizations")
            return {"status": "success"}
            
    def run_all_optimizations(self):
        """Run all available optimizations"""
        logger.info("Running all performance optimizations...")
        
        start_time = time.time()
        
        # Run all optimizations
        for opt in self.available_optimizations:
            method_name = f"optimize_{opt}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                self.results[opt] = method()
                
        end_time = time.time()
        total_time = end_time - start_time
        
        self.results["total_time"] = total_time
        logger.info(f"All optimizations completed in {total_time:.2f} seconds")
        
        return self.results
        
    def run_specific_optimizations(self, optimizations: List[str]):
        """Run specific optimizations"""
        logger.info(f"Running selected optimizations: {', '.join(optimizations)}")
        
        start_time = time.time()
        
        # Run selected optimizations
        for opt in optimizations:
            if opt in self.available_optimizations:
                method_name = f"optimize_{opt}"
                if hasattr(self, method_name):
                    method = getattr(self, method_name)
                    self.results[opt] = method()
            else:
                logger.warning(f"Unknown optimization: {opt}")
                
        end_time = time.time()
        total_time = end_time - start_time
        
        self.results["total_time"] = total_time
        logger.info(f"Selected optimizations completed in {total_time:.2f} seconds")
        
        return self.results
        
    def print_results(self):
        """Print optimization results"""
        if not self.results:
            logger.error("No optimization results to display")
            return
            
        print("\n" + "=" * 80)
        print("NVC BANKING PLATFORM PERFORMANCE OPTIMIZATION RESULTS")
        print("=" * 80)
        
        # Print each optimization result
        for opt, result in self.results.items():
            if opt == "total_time":
                continue
                
            print(f"\n{opt.upper()} OPTIMIZATION:")
            
            if isinstance(result, dict):
                for key, value in result.items():
                    print(f"  - {key}: {value}")
            else:
                print(f"  - {result}")
                
        # Print total time
        if "total_time" in self.results:
            print(f"\nTotal optimization time: {self.results['total_time']:.2f} seconds")
            
        print("\n" + "=" * 80)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="NVC Banking Platform Performance Manager")
    parser.add_argument("--all", action="store_true", help="Run all optimizations")
    parser.add_argument("--database", action="store_true", help="Optimize database")
    parser.add_argument("--memory", action="store_true", help="Optimize memory usage")
    parser.add_argument("--server", action="store_true", help="Optimize server configuration")
    parser.add_argument("--cache", action="store_true", help="Optimize cache settings")
    parser.add_argument("--templates", action="store_true", help="Optimize template rendering")
    parser.add_argument("--static", action="store_true", help="Optimize static file handling")
    parser.add_argument("--blockchain", action="store_true", help="Optimize blockchain interaction")
    parser.add_argument("--logging", action="store_true", help="Optimize logging configuration")
    
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Create performance manager
    manager = PerformanceManager()
    
    # Run optimizations
    if args.all:
        # Run all optimizations
        manager.run_all_optimizations()
    else:
        # Run selected optimizations
        optimizations = []
        if args.database:
            optimizations.append("database")
        if args.memory:
            optimizations.append("memory")
        if args.server:
            optimizations.append("server")
        if args.cache:
            optimizations.append("cache")
        if args.templates:
            optimizations.append("templates")
        if args.static:
            optimizations.append("static")
        if args.blockchain:
            optimizations.append("blockchain")
        if args.logging:
            optimizations.append("logging")
            
        # If no specific optimizations selected, run all
        if not optimizations:
            manager.run_all_optimizations()
        else:
            manager.run_specific_optimizations(optimizations)
    
    # Print results
    manager.print_results()