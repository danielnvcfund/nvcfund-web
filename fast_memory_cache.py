"""
Fast Memory Cache System

This module provides a simplified, high-performance memory cache
to replace the more complex memory_cache module. It focuses on:

1. Minimizing locking overhead
2. Reducing complexity
3. Preventing excessive database queries
"""

import logging
import threading
from functools import lru_cache
from typing import Dict, Tuple, Any, Optional

logger = logging.getLogger(__name__)

# Simple global cache with minimal locking
_RATE_CACHE: Dict[Tuple[str, str], float] = {}
_CACHE_LOCK = threading.RLock()

# LRU cache for high-frequency lookups
@lru_cache(maxsize=256)
def get_cached_rate(from_currency: str, to_currency: str) -> Optional[float]:
    """
    Get a cached exchange rate with minimal overhead
    
    Args:
        from_currency: Source currency code
        to_currency: Target currency code
        
    Returns:
        float: Exchange rate or None if not found
    """
    key = (str(from_currency), str(to_currency))
    
    # Fast path - check without lock
    if key in _RATE_CACHE:
        return _RATE_CACHE[key]
    return None

def cache_exchange_rate(from_currency: str, to_currency: str, rate: float) -> None:
    """
    Cache an exchange rate with minimal locking
    
    Args:
        from_currency: Source currency code
        to_currency: Target currency code
        rate: Exchange rate value
    """
    key = (str(from_currency), str(to_currency))
    
    with _CACHE_LOCK:
        _RATE_CACHE[key] = rate
    
    # Also cache the inverse rate
    if rate != 0:
        inverse_key = (str(to_currency), str(from_currency))
        inverse_rate = 1.0 / rate
        
        with _CACHE_LOCK:
            _RATE_CACHE[inverse_key] = inverse_rate

def clear_rate_cache() -> None:
    """Clear the entire rate cache"""
    with _CACHE_LOCK:
        _RATE_CACHE.clear()
    
    # Also clear the LRU cache
    get_cached_rate.cache_clear()

# Additional cache functions to match the original memory_cache API
def cache_value(key: str, value: Any, ttl: int = 3600) -> None:
    """Simple stub to maintain API compatibility"""
    pass

def get_cached_value(key: str) -> Optional[Any]:
    """Simple stub to maintain API compatibility"""
    return None

# Public API compatible with the original memory_cache
__all__ = [
    'get_cached_rate',
    'cache_exchange_rate',
    'clear_rate_cache',
    'cache_value',
    'get_cached_value'
]