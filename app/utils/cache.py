"""
Cache utilities for Cloud Run.
Uses Redis (Cloud Memorystore) for caching data between requests.
"""
import logging
import pickle
from typing import Any, Optional, Callable
from functools import wraps
import pandas as pd

logger = logging.getLogger(__name__)


def cache_key_builder(*args, **kwargs) -> str:
    """Build cache key from function arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    return ":".join(key_parts)


def cached(timeout: int = 3600, key_prefix: str = ""):
    """
    Decorator for caching function results.

    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache key

    Usage:
        @cached(timeout=3600, key_prefix="report")
        def get_report_data(customer_id):
            return expensive_operation(customer_id)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import current_app

            # Build cache key
            cache_key = f"{key_prefix}:{func.__name__}:{cache_key_builder(*args, **kwargs)}"

            # Try to get from cache
            cache = current_app.extensions.get('cache')
            if cache:
                try:
                    cached_value = cache.get(cache_key)
                    if cached_value is not None:
                        logger.debug(f"Cache hit for {cache_key}")
                        return cached_value
                except Exception as e:
                    logger.warning(f"Cache get error for {cache_key}: {e}")

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            if cache:
                try:
                    cache.set(cache_key, result, timeout=timeout)
                    logger.debug(f"Cached result for {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache set error for {cache_key}: {e}")

            return result

        return wrapper
    return decorator


def cache_dataframe(cache, key: str, df: pd.DataFrame, timeout: int = 3600):
    """
    Cache a pandas DataFrame.

    Args:
        cache: Flask-Caching instance
        key: Cache key
        df: DataFrame to cache
        timeout: Cache timeout in seconds
    """
    try:
        # Serialize DataFrame to pickle
        serialized = pickle.dumps(df)
        cache.set(key, serialized, timeout=timeout)
        logger.debug(f"Cached DataFrame with key {key}")
    except Exception as e:
        logger.error(f"Error caching DataFrame: {e}")


def get_cached_dataframe(cache, key: str) -> Optional[pd.DataFrame]:
    """
    Retrieve a cached DataFrame.

    Args:
        cache: Flask-Caching instance
        key: Cache key

    Returns:
        DataFrame if found, None otherwise
    """
    try:
        serialized = cache.get(key)
        if serialized:
            df = pickle.loads(serialized)
            logger.debug(f"Retrieved cached DataFrame with key {key}")
            return df
    except Exception as e:
        logger.error(f"Error retrieving cached DataFrame: {e}")

    return None


def invalidate_cache_pattern(cache, pattern: str):
    """
    Invalidate all cache keys matching a pattern.

    Args:
        cache: Flask-Caching instance
        pattern: Pattern to match (e.g., "report:*")
    """
    try:
        # This requires Redis backend
        if hasattr(cache.cache, '_write_client'):
            redis_client = cache.cache._write_client
            keys = redis_client.keys(f"flask_cache_{pattern}")
            if keys:
                redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache keys matching {pattern}")
    except Exception as e:
        logger.error(f"Error invalidating cache pattern {pattern}: {e}")
