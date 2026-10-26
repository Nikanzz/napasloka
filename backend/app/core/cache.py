"""Thread-safe in-memory caching for machine learning models and evaluation data."""

from collections import OrderedDict
import logging
import threading

logger = logging.getLogger(__name__)


class MemoryCache:
    """Thread-safe LRU in-memory cache for trained estimators and artifacts."""

    def __init__(self, maxsize=128):
        self._maxsize = maxsize
        self._cache = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key):
        """Retrieve an item from cache, marking it as most recently used."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def set(self, key, value):
        """Store an item in cache, evicting the least recently used if exceeding maxsize."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._maxsize:
                oldest_key, _ = self._cache.popitem(last=False)
                logger.debug("Evicted oldest cache entry: %s", oldest_key)

    def contains(self, key):
        """Check if key exists in cache without modifying LRU order."""
        with self._lock:
            return key in self._cache

    def remove(self, key):
        """Remove a specific key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self):
        """Return cache hit/miss statistics and current size."""
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = (self._hits / total) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "maxsize": self._maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": round(hit_ratio, 4),
            }


# Global model cache (can hold up to 16 models in memory)
model_cache = MemoryCache(maxsize=16)

# Global test predictions cache (holds parsed DataFrames for fast slicing)
predictions_cache = MemoryCache(maxsize=16)
