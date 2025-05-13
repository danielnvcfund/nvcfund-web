"""
Simple caching utility to improve performance
"""
import os
import json
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_path(cache_key):
    """Get the path to a cache file"""
    return os.path.join(CACHE_DIR, f"{cache_key}.json")

def cache_data(data, cache_key, expire_seconds=3600):
    """
    Cache data to a file
    
    Args:
        data: The data to cache (must be JSON serializable)
        cache_key (str): Key to identify the cached data
        expire_seconds (int): Time in seconds until cache expires
    """
    try:
        cache_path = get_cache_path(cache_key)
        
        cache_data = {
            'data': data,
            'expires_at': time.time() + expire_seconds
        }
        
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)
            
        logger.debug(f"Cached data with key: {cache_key}")
        return True
    except Exception as e:
        logger.error(f"Error caching data: {str(e)}")
        return False

def get_cached_data(cache_key):
    """
    Get data from cache
    
    Args:
        cache_key (str): Key to identify the cached data
        
    Returns:
        The cached data or None if no valid cache exists
    """
    try:
        cache_path = get_cache_path(cache_key)
        
        if not os.path.exists(cache_path):
            return None
            
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
            
        # Check if cache has expired
        if time.time() > cache_data.get('expires_at', 0):
            logger.debug(f"Cache expired for key: {cache_key}")
            os.remove(cache_path)  # Remove expired cache
            return None
            
        logger.debug(f"Retrieved cached data with key: {cache_key}")
        return cache_data.get('data')
    except Exception as e:
        logger.error(f"Error getting cached data: {str(e)}")
        return None

def clear_cache(cache_key=None):
    """
    Clear specific cache or all caches
    
    Args:
        cache_key (str, optional): Key to identify the specific cache to clear.
                                  If None, all caches are cleared.
    """
    try:
        if cache_key:
            cache_path = get_cache_path(cache_key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
                logger.debug(f"Cleared cache with key: {cache_key}")
        else:
            # Clear all caches
            for filename in os.listdir(CACHE_DIR):
                if filename.endswith('.json'):
                    os.remove(os.path.join(CACHE_DIR, filename))
            logger.debug("Cleared all caches")
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")

def cached(expire_seconds=3600, key_prefix=''):
    """
    Decorator to cache function results
    
    Args:
        expire_seconds (int): Time in seconds until cache expires
        key_prefix (str): Prefix for the cache key
        
    Usage:
        @cached(expire_seconds=300, key_prefix='user_data')
        def get_user_data(user_id):
            # Expensive operation
            return data
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name, args, and kwargs
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            
            cache_key = "_".join(key_parts)
            
            # Try to get from cache first
            cached_result = get_cached_data(cache_key)
            if cached_result is not None:
                return cached_result
                
            # Cache miss, call the function
            result = func(*args, **kwargs)
            
            # Cache the result
            cache_data(result, cache_key, expire_seconds)
            
            return result
        return wrapper
    return decorator

# Blockchain connection cache expiry (5 minutes)
WEB3_CACHE_EXPIRY = 300  # seconds
