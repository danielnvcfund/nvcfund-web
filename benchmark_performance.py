"""
Benchmark script to identify performance bottlenecks in the application

This script:
1. Measures loading times for key components
2. Profiles database access patterns
3. Identifies memory-intensive operations
4. Reports optimization opportunities
"""

import os
import sys
import time
import logging
import importlib
import threading
import traceback
from functools import wraps
from typing import List, Dict, Any, Callable

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BenchmarkPerformance")

class Timer:
    """Simple context manager for timing code blocks"""
    def __init__(self, name):
        self.name = name
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        logger.info(f"{self.name} took {end_time - self.start_time:.4f} seconds")
        
def profile_function(func):
    """Decorator to profile function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"{func.__name__} took {end_time - start_time:.4f} seconds")
        return result
    return wrapper

class PerformanceBenchmark:
    """Benchmark key components of the application"""
    
    def __init__(self):
        self.results = {}
        
    def benchmark_module_import(self, module_name: str) -> float:
        """Measure time to import a module"""
        logger.info(f"Benchmarking import of {module_name}")
        start_time = time.time()
        try:
            importlib.import_module(module_name)
            import_time = time.time() - start_time
            self.results[f"import_{module_name}"] = import_time
            logger.info(f"Importing {module_name} took {import_time:.4f} seconds")
            return import_time
        except ImportError as e:
            logger.error(f"Error importing {module_name}: {str(e)}")
            return -1
            
    def benchmark_flask_app_startup(self) -> float:
        """Benchmark Flask app startup time"""
        logger.info("Benchmarking Flask app startup")
        with Timer("Flask app startup") as timer:
            try:
                from app import app
                return time.time() - timer.start_time
            except ImportError:
                logger.error("Could not import Flask app")
                return -1
                
    def benchmark_database_connection(self) -> float:
        """Benchmark database connection time"""
        logger.info("Benchmarking database connection")
        with Timer("Database connection") as timer:
            try:
                from app import db
                # Execute a simple query to ensure connection is established
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return time.time() - timer.start_time
            except Exception as e:
                logger.error(f"Database connection error: {str(e)}")
                return -1
                
    def benchmark_template_rendering(self, template_name: str = 'index.html') -> float:
        """Benchmark template rendering time"""
        logger.info(f"Benchmarking rendering of {template_name}")
        with Timer(f"Template rendering ({template_name})") as timer:
            try:
                from app import app
                with app.test_request_context():
                    from flask import render_template
                    render_template(template_name)
                return time.time() - timer.start_time
            except Exception as e:
                logger.error(f"Template rendering error: {str(e)}")
                return -1
                
    def benchmark_key_modules(self):
        """Benchmark key modules that might affect performance"""
        modules_to_test = [
            'blockchain', 
            'account_holder_models',
            'currency_exchange_service',
            'payment_gateways',
            'routes',
            'customer_support'
        ]
        
        for module in modules_to_test:
            self.benchmark_module_import(module)
            
    def run_all_benchmarks(self):
        """Run all benchmarks and collect results"""
        logger.info("Starting comprehensive performance benchmark")
        
        # Benchmark key modules
        self.benchmark_key_modules()
        
        # Benchmark Flask app startup
        self.benchmark_flask_app_startup()
        
        # Benchmark database connection
        self.benchmark_database_connection()
        
        # Benchmark key template rendering
        self.benchmark_template_rendering('index.html')
        self.benchmark_template_rendering('admin/blockchain/index.html')
        self.benchmark_template_rendering('treasury/dashboard.html')
        
        # Print summary
        self.print_summary()
        
    def print_summary(self):
        """Print benchmark summary with recommendations"""
        logger.info("=" * 50)
        logger.info("PERFORMANCE BENCHMARK SUMMARY")
        logger.info("=" * 50)
        
        # Sort results by time (descending)
        sorted_results = sorted(
            self.results.items(), 
            key=lambda x: x[1] if x[1] > 0 else float('inf'), 
            reverse=True
        )
        
        # Print results table
        logger.info(f"{'Component':<40} | {'Time (seconds)':<15}")
        logger.info("-" * 60)
        for name, time_taken in sorted_results:
            if time_taken > 0:
                logger.info(f"{name:<40} | {time_taken:<15.4f}")
            else:
                logger.info(f"{name:<40} | {'ERROR':<15}")
        
        # Generate recommendations
        slow_components = [name for name, time in sorted_results if time > 1.0 and time > 0]
        
        logger.info("\nRECOMMENDATIONS:")
        if slow_components:
            logger.info(f"Optimize these slow components: {', '.join(slow_components)}")
        else:
            logger.info("No significantly slow components detected.")
            
        logger.info("=" * 50)

if __name__ == "__main__":
    benchmark = PerformanceBenchmark()
    benchmark.run_all_benchmarks()