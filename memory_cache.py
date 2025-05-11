"""
Memory Cache for NVC Banking Platform

This module provides a simple in-memory cache with TTL (time-to-live) for
frequently accessed database records and computed values.
"""

import time
import threading
import logging
from collections import OrderedDict
from functools import wraps

logger = logging.getLogger(__name__)

class MemoryCache:
    """Simple in-memory cache with TTL"""
    
    def __init__(self, max_size=1000, default_ttl=300):
        """
        Initialize cache with maximum size and default TTL
        
        Args:
            max_size (int): Maximum number of items in cache
            default_ttl (int): Default time-to-live in seconds
        """
        self._cache = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0
        }
    
    def get(self, key, default=None):
        """
        Get a value from the cache
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                # Check if expired
                if expiry is None or time.time() < expiry:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    self._stats['hits'] += 1
                    return value
                else:
                    # Expired - remove and return default
                    del self._cache[key]
                    self._stats['misses'] += 1
            else:
                self._stats['misses'] += 1
            return default
    
    def set(self, key, value, ttl=None):
        """
        Set a value in the cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for no expiry)
        """
        with self._lock:
            # Calculate expiry time
            expiry = None if ttl is None else time.time() + (ttl or self._default_ttl)
            
            # If key exists, update it
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = (value, expiry)
                self._stats['sets'] += 1
                return
            
            # If cache is full, remove oldest item
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)  # Remove first item (oldest)
                self._stats['evictions'] += 1
            
            # Add new item
            self._cache[key] = (value, expiry)
            self._stats['sets'] += 1
    
    def delete(self, key):
        """Delete a key from the cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        """Clear the entire cache"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self):
        """Get cache statistics"""
        with self._lock:
            stats = self._stats.copy()
            stats['size'] = len(self._cache)
            stats['max_size'] = self._max_size
            return stats

# Create shared cache instances for different purposes
account_cache = MemoryCache(max_size=500, default_ttl=300)  # 5 minutes
rate_cache = MemoryCache(max_size=200, default_ttl=600)     # 10 minutes
dashboard_cache = MemoryCache(max_size=100, default_ttl=60) # 1 minute

def cached(cache, key_func=None, ttl=None):
    """
    Decorator for caching function results
    
    Args:
        cache (MemoryCache): Cache instance to use
        key_func (callable): Function to generate cache key from args and kwargs
        ttl (int): Time-to-live in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default: function name + args + sorted kwargs
                key = f"{func.__module__}.{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Check cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            if result is not None:  # Don't cache None results
                cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Utility functions for common caching patterns

def cache_account(account_id, account_data, ttl=300):
    """Cache account data"""
    account_cache.set(f"account:{account_id}", account_data, ttl)

def get_cached_account(account_id):
    """Get cached account data"""
    return account_cache.get(f"account:{account_id}")

def cache_exchange_rate(from_currency, to_currency, rate, ttl=600):
    """Cache exchange rate"""
    rate_cache.set(f"rate:{from_currency}:{to_currency}", rate, ttl)

def get_cached_exchange_rate(from_currency, to_currency):
    """Get cached exchange rate"""
    return rate_cache.get(f"rate:{from_currency}:{to_currency}")

def cache_dashboard_data(user_id, data, ttl=60):
    """Cache dashboard data"""
    dashboard_cache.set(f"dashboard:{user_id}", data, ttl)

def get_cached_dashboard_data(user_id):
    """Get cached dashboard data"""
    return dashboard_cache.get(f"dashboard:{user_id}")

def invalidate_account_cache(account_id):
    """Invalidate account cache"""
    account_cache.delete(f"account:{account_id}")

def invalidate_rate_cache(from_currency=None, to_currency=None):
    """Invalidate exchange rate cache"""
    if from_currency and to_currency:
        rate_cache.delete(f"rate:{from_currency}:{to_currency}")
    else:
        # If no specific currencies, clear all rate cache
        rate_cache.clear()

def invalidate_dashboard_cache(user_id=None):
    """Invalidate dashboard cache"""
    if user_id:
        dashboard_cache.delete(f"dashboard:{user_id}")
    else:
        dashboard_cache.clear()

def get_cache_stats():
    """Get statistics from all caches"""
    return {
        'account_cache': account_cache.get_stats(),
        'rate_cache': rate_cache.get_stats(),
        'dashboard_cache': dashboard_cache.get_stats()
    }