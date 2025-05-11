"""
Response Cache for NVC Banking Platform

This module provides HTTP response caching for Flask routes.
"""

import time
import logging
import functools
from flask import request, make_response
import hashlib
import threading

# Set up logging
logger = logging.getLogger(__name__)

class ResponseCache:
    """Simple in-memory cache for HTTP responses"""
    
    def __init__(self, max_size=100, default_ttl=60):
        """
        Initialize cache
        
        Args:
            max_size (int): Maximum number of cached responses
            default_ttl (int): Default TTL in seconds
        """
        self._cache = {}
        self._expiry = {}
        self._access_times = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0
        }
    
    def _generate_key(self, request):
        """Generate cache key from request"""
        # Create a key based on path and query string
        key_parts = [
            request.path,
            request.query_string.decode('utf-8'),
        ]
        
        # Add selected headers that affect response
        for header in ['Accept', 'Accept-Encoding', 'Accept-Language']:
            if header in request.headers:
                key_parts.append(f"{header}:{request.headers[header]}")
        
        # Generate hash
        key = hashlib.md5(':'.join(key_parts).encode('utf-8')).hexdigest()
        return key
    
    def get(self, request):
        """
        Get cached response for a request
        
        Args:
            request: Flask request object
            
        Returns:
            Cached response or None
        """
        key = self._generate_key(request)
        with self._lock:
            # Check if response is in cache and not expired
            if key in self._cache and (
                    self._expiry[key] is None or 
                    time.time() < self._expiry[key]):
                # Update access time
                self._access_times[key] = time.time()
                self._stats['hits'] += 1
                return self._cache[key]
            elif key in self._cache:
                # Expired - remove from cache
                self._remove(key)
            
            self._stats['misses'] += 1
            return None
    
    def set(self, request, response, ttl=None):
        """
        Cache a response
        
        Args:
            request: Flask request object
            response: Response to cache
            ttl: Time-to-live in seconds or None for default
        """
        key = self._generate_key(request)
        expiry = None if ttl is None else time.time() + (ttl or self._default_ttl)
        
        with self._lock:
            # Check cache size and evict if necessary
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_one()
            
            # Store response
            self._cache[key] = response
            self._expiry[key] = expiry
            self._access_times[key] = time.time()
            self._stats['sets'] += 1
    
    def _remove(self, key):
        """Remove an item from the cache"""
        if key in self._cache:
            del self._cache[key]
        if key in self._expiry:
            del self._expiry[key]
        if key in self._access_times:
            del self._access_times[key]
    
    def _evict_one(self):
        """Evict the least recently used item"""
        if not self._access_times:
            return
            
        # Find oldest accessed item
        oldest_key = min(self._access_times.items(), key=lambda x: x[1])[0]
        self._remove(oldest_key)
        self._stats['evictions'] += 1
    
    def clear(self):
        """Clear the cache"""
        with self._lock:
            self._cache.clear()
            self._expiry.clear()
            self._access_times.clear()
    
    def get_stats(self):
        """Get cache statistics"""
        with self._lock:
            stats = self._stats.copy()
            stats['size'] = len(self._cache)
            stats['max_size'] = self._max_size
            return stats


# Create a global cache instance
response_cache = ResponseCache(max_size=500, default_ttl=60)

def cache_response(ttl=None, unless=None):
    """
    Decorator to cache view responses
    
    Args:
        ttl: Time-to-live in seconds or None for default
        unless: Function that returns True if response should not be cached
        
    Returns:
        Decorated function
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(*args, **kwargs):
            # Skip caching for non-GET requests
            if request.method != 'GET':
                return view_func(*args, **kwargs)
            
            # Skip caching based on unless condition
            if unless and unless():
                return view_func(*args, **kwargs)
            
            # Check cache
            cached_response = response_cache.get(request)
            if cached_response:
                return cached_response
            
            # Call view function
            response = view_func(*args, **kwargs)
            
            # Cache the response
            # Only cache successful responses
            if response.status_code == 200:
                # Convert to response object if needed
                if not hasattr(response, 'status_code'):
                    response = make_response(response)
                    
                # Add cache headers
                if ttl:
                    response.headers['X-Cache-TTL'] = str(ttl)
                
                # Cache the response
                response_cache.set(request, response, ttl)
            
            return response
        return wrapper
    return decorator

def clear_response_cache():
    """Clear the response cache"""
    response_cache.clear()
    logger.info("Response cache cleared")

def get_cache_stats():
    """Get cache statistics"""
    return response_cache.get_stats()