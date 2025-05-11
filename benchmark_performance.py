#!/usr/bin/env python3
"""
Benchmark Performance for NVC Banking Platform

This script measures the performance of key pages in the NVC Banking Platform
and generates a report of load times.
"""

import time
import requests
import statistics
import logging
import os
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("benchmark")

# Set base URL (default to localhost:5000)
BASE_URL = os.environ.get("BENCHMARK_URL", "http://localhost:5000")

# Pages to benchmark
PAGES = [
    "/",  # Home page
    "/auth/login",  # Login page
    "/dashboard/overview",  # Dashboard
    "/currency-exchange/",  # Currency Exchange
    "/account-holders/",  # Account Holders page
    "/documents/",  # Documents page
    "/api/healthcheck",  # Health check endpoint
    "/stablecoin/settlement",  # Stablecoin settlement
    "/correspondent-banking",  # Correspondent banking
]

# Number of requests per page
NUM_REQUESTS = 3

def measure_page_load_time(url):
    """Measure the load time for a specific URL"""
    full_url = f"{BASE_URL}{url}"
    
    try:
        start_time = time.time()
        response = requests.get(full_url, timeout=10)
        end_time = time.time()
        
        load_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Get content size safely
        size = len(response.content) if response.content else 0
        
        # Check if the request was successful
        if response.status_code == 200:
            return load_time, response.status_code, size
        else:
            logger.warning(f"Request to {url} returned status code {response.status_code}")
            return load_time, response.status_code, size
    
    except requests.RequestException as e:
        logger.error(f"Error requesting {url}: {str(e)}")
        return None, None, 0

def run_benchmark():
    """Run benchmarks for all pages"""
    results = {}
    
    print(f"\n{'=' * 60}")
    print(f"NVC Banking Platform Performance Benchmark")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}\n")
    
    for page in PAGES:
        print(f"Testing {page}...")
        page_times = []
        
        for i in range(NUM_REQUESTS):
            load_time, status_code, size = measure_page_load_time(page)
            
            if load_time is not None:
                page_times.append(load_time)
                size_kb = size/1024 if size else 0
                print(f"  Request {i+1}: {load_time:.2f}ms (Status: {status_code}, Size: {size_kb:.1f}KB)")
            else:
                print(f"  Request {i+1}: Failed")
            
            # Sleep briefly between requests
            time.sleep(0.5)
        
        if page_times:
            avg_time = statistics.mean(page_times)
            min_time = min(page_times)
            max_time = max(page_times)
            results[page] = {
                'avg': avg_time,
                'min': min_time,
                'max': max_time,
                'samples': len(page_times)
            }
            print(f"  Summary: Avg {avg_time:.2f}ms, Min {min_time:.2f}ms, Max {max_time:.2f}ms\n")
        else:
            print(f"  Summary: All requests failed\n")
            results[page] = {
                'avg': None,
                'min': None,
                'max': None,
                'samples': 0
            }
    
    return results

def generate_report(results):
    """Generate a performance report"""
    print(f"\n{'=' * 60}")
    print(f"PERFORMANCE SUMMARY REPORT")
    print(f"{'=' * 60}")
    print(f"{'Page':<20} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Samples'}")
    print(f"{'-' * 60}")
    
    for page, data in results.items():
        if data['avg'] is not None:
            print(f"{page:<20} {data['avg']:<12.2f} {data['min']:<12.2f} {data['max']:<12.2f} {data['samples']}")
        else:
            print(f"{page:<20} {'FAILED':<12} {'FAILED':<12} {'FAILED':<12} {data['samples']}")
    
    print(f"{'=' * 60}")
    print("Recommendations:")
    
    # Generate recommendations based on results
    slow_pages = [page for page, data in results.items() if data['avg'] and data['avg'] > 1000]
    if slow_pages:
        print(f"- Optimize slow pages: {', '.join(slow_pages)}")
    
    failed_pages = [page for page, data in results.items() if data['avg'] is None]
    if failed_pages:
        print(f"- Fix failed pages: {', '.join(failed_pages)}")
    
    print("\nBenchmark completed.")

if __name__ == "__main__":
    results = run_benchmark()
    generate_report(results)