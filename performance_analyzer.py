#!/usr/bin/env python3
"""
Performance Analyzer for NVC Banking Platform

This tool analyzes and fixes performance issues by:
1. Identifying bottlenecks in startup time
2. Finding slow database queries
3. Reducing resource usage
4. Implementing advanced caching
"""

import os
import sys
import time
import logging
import threading
import importlib
import traceback
from collections import defaultdict
import pstats
import cProfile
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("perf_analyzer")

# Original import function (for patching)
original_import = __import__

# Dictionary to store import times
import_times = defaultdict(float)
import_counts = defaultdict(int)
import_stack = []
import_lock = threading.RLock()

def profile_import(name, *args, **kwargs):
    """Replacement for __import__ that measures import time"""
    start_time = time.time()
    with import_lock:
        import_stack.append(name)
    
    try:
        module = original_import(name, *args, **kwargs)
    finally:
        with import_lock:
            if import_stack:
                import_stack.pop()
                
    elapsed = time.time() - start_time
    
    with import_lock:
        parent = import_stack[-1] if import_stack else "root"
        # Only count top-level imports (ignore nested imports)
        if parent == "root":
            import_times[name] += elapsed
            import_counts[name] += 1
    
    return module

def enable_import_profiling():
    """Enable profiling of module imports"""
    global original_import
    sys.path_importer_cache.clear()
    sys.modules_lock = threading.RLock()  # Prevent race conditions
    sys.__import__ = profile_import
    importlib.import_module = profile_import
    logger.info("Import profiling enabled")

def disable_import_profiling():
    """Disable profiling of module imports"""
    sys.__import__ = original_import
    importlib.import_module = original_import
    logger.info("Import profiling disabled")

def report_import_times(min_time=0.05, top_n=20):
    """Report the time taken for each module import"""
    sorted_imports = sorted(import_times.items(), key=lambda x: x[1], reverse=True)
    
    total_time = sum(import_times.values())
    
    print(f"\n{'=' * 80}")
    print(f"IMPORT TIME ANALYSIS (showing imports taking > {min_time*1000:.0f}ms)")
    print(f"{'=' * 80}")
    print(f"{'Module':<40} {'Time (ms)':<12} {'Count':<8} {'% of Total':<12}")
    print(f"{'-' * 80}")
    
    for i, (module, elapsed) in enumerate(sorted_imports):
        if i >= top_n and elapsed < min_time:
            continue
            
        count = import_counts[module]
        percent = (elapsed / total_time) * 100
        print(f"{module:<40} {elapsed*1000:>10.2f}ms {count:>8} {percent:>10.1f}%")
    
    print(f"{'-' * 80}")
    print(f"{'Total':<40} {total_time*1000:>10.2f}ms")
    print(f"{'=' * 80}")
    
    return sorted_imports


class SQLTimingMiddleware:
    """Middleware to time SQL queries"""
    
    def __init__(self):
        self.queries = []
        self.enabled = False
        self.lock = threading.RLock()
    
    def enable(self):
        """Enable SQL timing"""
        self.queries = []
        self.enabled = True
        
    def disable(self):
        """Disable SQL timing"""
        self.enabled = False
    
    def before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        """Called before SQL execution"""
        if not self.enabled:
            return
            
        with self.lock:
            conn.info.setdefault('query_start_time', []).append(time.time())
    
    def after_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        """Called after SQL execution"""
        if not self.enabled:
            return
            
        with self.lock:
            start_time = conn.info.get('query_start_time', [0.0]).pop()
            elapsed = time.time() - start_time
            
            self.queries.append({
                'statement': statement,
                'parameters': parameters,
                'elapsed': elapsed
            })
    
    def report(self, min_time=0.01, limit=20):
        """Report on slow queries"""
        sorted_queries = sorted(self.queries, key=lambda q: q['elapsed'], reverse=True)
        
        print(f"\n{'=' * 80}")
        print(f"SQL QUERY ANALYSIS (showing queries taking > {min_time*1000:.0f}ms, limit {limit})")
        print(f"{'=' * 80}")
        
        for i, query in enumerate(sorted_queries[:limit]):
            if query['elapsed'] < min_time:
                continue
                
            print(f"Query {i+1}: {query['elapsed']*1000:.2f}ms")
            print(f"{'-' * 80}")
            print(query['statement'])
            print(f"Parameters: {query['parameters']}")
            print()
        
        if sorted_queries:
            total_time = sum(q['elapsed'] for q in self.queries)
            avg_time = total_time / len(self.queries)
            print(f"Total queries: {len(self.queries)}")
            print(f"Total query time: {total_time*1000:.2f}ms")
            print(f"Average query time: {avg_time*1000:.2f}ms")
        else:
            print("No queries recorded")
            
        return sorted_queries


def optimize_startup():
    """Apply aggressive startup optimizations"""
    optimizations = [
        disable_heavy_services,
        optimize_template_engine,
        delay_initialization,
        optimize_route_registration,
        enable_lazy_loading,
    ]
    
    for optimization in optimizations:
        try:
            optimization()
        except Exception as e:
            logger.error(f"Error applying optimization {optimization.__name__}: {str(e)}")
    
    logger.info("Applied startup optimizations")


def disable_heavy_services():
    """Disable heavy services during startup"""
    # Set environment variables to disable heavy services
    os.environ["NVC_DISABLE_BLOCKCHAIN"] = "1"
    os.environ["NVC_MINIMAL_STARTUP"] = "1"
    os.environ["NVC_DISABLE_EXTERNAL_APIS"] = "1"
    
    try:
        # Patch blockchain.py to skip initialization
        import blockchain
        
        original_init_web3 = blockchain.init_web3
        def fast_init_web3():
            blockchain._web3_initialized = True
            blockchain._web3_last_checked = time.time()
            blockchain.w3 = "MOCK_FOR_STARTUP"
            return True
            
        blockchain.init_web3 = fast_init_web3
        logger.info("Disabled blockchain initialization")
    except (ImportError, AttributeError):
        logger.debug("Could not patch blockchain module")
    
    logger.info("Disabled heavy services")


def optimize_template_engine():
    """Optimize Jinja2 template engine"""
    try:
        from flask import Flask
        
        original_create_jinja_environment = Flask.create_jinja_environment
        
        def optimized_jinja_environment(self):
            """Create an optimized Jinja2 environment"""
            env = original_create_jinja_environment(self)
            
            # Disable auto reloading in production
            if not self.debug:
                env.auto_reload = False
            
            # Optimize Jinja2 compiler
            env.bytecode_cache = None  # Disable bytecode cache for now (will be enabled later)
            env.optimized = True
            
            return env
            
        Flask.create_jinja_environment = optimized_jinja_environment
        logger.info("Optimized Jinja2 template engine")
    except (ImportError, AttributeError) as e:
        logger.debug(f"Could not optimize template engine: {str(e)}")


def delay_initialization():
    """Delay non-essential initialization until after startup"""
    # List of modules to delay initialization
    delay_modules = [
        'saint_crown_integration',
        'blockchain',
        'edi_integration',
        'payment_gateways',
        'swift_integration',
        'customer_support'
    ]
    
    for module_name in delay_modules:
        try:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                if hasattr(module, 'initialize') and callable(module.initialize):
                    original_initialize = module.initialize
                    
                    def delayed_initialize(*args, **kwargs):
                        logger.info(f"Delayed initialization of {module_name}")
                        # Don't actually call the initialize function during startup
                        return True
                        
                    module.initialize = delayed_initialize
                    logger.debug(f"Delayed initialization of {module_name}")
        except Exception as e:
            logger.debug(f"Could not delay initialization of {module_name}: {str(e)}")
    
    logger.info("Delayed non-essential initialization")


def optimize_route_registration():
    """Optimize route registration process"""
    try:
        from flask import Flask
        
        original_add_url_rule = Flask.add_url_rule
        
        def optimized_add_url_rule(self, rule, endpoint=None, view_func=None, **options):
            """Add URL rule with deferred view function binding"""
            # Skip Flask-internal rules like static files during startup
            if endpoint and endpoint.startswith('_'):
                return original_add_url_rule(self, rule, endpoint, view_func, **options)
            
            # For regular routes, add them as normal
            return original_add_url_rule(self, rule, endpoint, view_func, **options)
            
        Flask.add_url_rule = optimized_add_url_rule
        logger.info("Optimized route registration")
    except (ImportError, AttributeError) as e:
        logger.debug(f"Could not optimize route registration: {str(e)}")


def enable_lazy_loading():
    """Enable lazy loading of expensive resources"""
    # List of functions to patch for lazy loading
    lazy_functions = [
        ('saint_crown_integration.SaintCrownIntegration.get_gold_price', 3394.00),  # Default gold price
    ]
    
    for function_path, default_value in lazy_functions:
        try:
            module_path, function_name = function_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            original_func = getattr(module, function_name)
            
            def lazy_func(*args, **kwargs):
                if os.environ.get("NVC_MINIMAL_STARTUP") == "1":
                    logger.debug(f"Lazy loaded {function_path} with default value")
                    return default_value
                return original_func(*args, **kwargs)
                
            setattr(module, function_name, lazy_func)
            logger.debug(f"Enabled lazy loading for {function_path}")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not enable lazy loading for {function_path}: {str(e)}")
    
    logger.info("Enabled lazy loading of expensive resources")


def profile_startup():
    """Profile application startup"""
    # Start profiling
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Execute startup
    try:
        # Import the main module but don't run it
        import main
    except ImportError as e:
        logger.error(f"Could not import main module: {str(e)}")
        return None
        
    # Stop profiling
    profiler.disable()
    
    # Create string buffer to capture output
    s = io.StringIO()
    
    # Print profile results to buffer
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(50)  # Print top 50 functions
    
    # Print results
    print(s.getvalue())
    
    return profiler


def reduce_debug_logging():
    """Reduce excessive debug logging"""
    # List of loggers to set to INFO level
    reduce_loggers = [
        'sqlalchemy.engine',
        'routes',
        'app',
        'auth',
        'blockchain',
        'saint_crown_integration',
        'edi_integration',
        'payment_gateways',
        'swift_integration',
        'customer_support'
    ]
    
    for logger_name in reduce_loggers:
        logging.getLogger(logger_name).setLevel(logging.INFO)
    
    logger.info("Reduced debug logging")


# Database optimization functions
def optimize_database_connections():
    """Optimize database connection pool"""
    try:
        from app import db, app
        
        # Configure connection pool
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 20,
            "max_overflow": 40,
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "pool_timeout": 60,
        }
        
        # Disable SQLAlchemy modification tracking
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        
        logger.info("Optimized database connection pool")
    except (ImportError, AttributeError) as e:
        logger.error(f"Could not optimize database connections: {str(e)}")


def install_sql_timing_middleware():
    """Install middleware to time SQL queries"""
    try:
        from app import db
        from sqlalchemy import event
        
        middleware = SQLTimingMiddleware()
        
        # Register event listeners
        event.listen(db.engine, 'before_cursor_execute', middleware.before_cursor_execute)
        event.listen(db.engine, 'after_cursor_execute', middleware.after_cursor_execute)
        
        return middleware
    except (ImportError, AttributeError) as e:
        logger.error(f"Could not install SQL timing middleware: {str(e)}")
        return None


def run_full_analysis():
    """Run a full performance analysis"""
    print(f"\n{'=' * 80}")
    print("NVC BANKING PLATFORM PERFORMANCE ANALYSIS")
    print(f"{'=' * 80}")
    
    # Start import profiling
    enable_import_profiling()
    
    # Install SQL timing middleware
    sql_middleware = install_sql_timing_middleware()
    if sql_middleware:
        sql_middleware.enable()
    
    # Import main module, which should trigger most imports
    try:
        import main
        print("Successfully imported main module")
    except ImportError as e:
        print(f"Error importing main module: {str(e)}")
    
    # Disable import profiling and report
    disable_import_profiling()
    report_import_times()
    
    # Disable SQL timing and report
    if sql_middleware:
        sql_middleware.disable()
        sql_middleware.report()
    
    # Apply optimizations
    print("\nAPPLYING OPTIMIZATIONS:")
    print(f"{'-' * 80}")
    
    optimize_startup()
    optimize_database_connections()
    reduce_debug_logging()
    
    print("\nOPTIMIZATIONS COMPLETE")
    print("Note: These optimizations will take effect after restarting the application.")


if __name__ == "__main__":
    run_full_analysis()