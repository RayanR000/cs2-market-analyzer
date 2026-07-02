import time
from functools import wraps
from typing import Any, Callable

_cache: dict[str, tuple[float, Any]] = {}
_default_ttl = 60


def cached(ttl: int = _default_ttl):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            now = time.monotonic()
            if key in _cache:
                expires, value = _cache[key]
                if now < expires:
                    return value
            result = func(*args, **kwargs)
            _cache[key] = (now + ttl, result)
            return result
        return wrapper
    return decorator


def cached_method(ttl: int = _default_ttl):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            key = f"{func.__name__}:{id(self)}:{args}:{kwargs}"
            now = time.monotonic()
            if key in _cache:
                expires, value = _cache[key]
                if now < expires:
                    return value
            result = func(self, *args, **kwargs)
            _cache[key] = (now + ttl, result)
            return result
        return wrapper
    return decorator


def clear_cache():
    _cache.clear()
