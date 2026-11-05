class MemoryCache:
    def __init__(self, maxsize=128):
        """Initialize in-memory LRU cache with a maximum capacity."""
        self._maxsize = maxsize
        self._cache = {}
        self._hits = 0

    def get(self, key):
        """Retrieve a cached item by key, incrementing the hit counter."""
        if key in self._cache:
            self._hits += 1
            return self._cache[key]
        return None

    def set(self, key, value):
        """Store a value in cache, evicting the oldest item if capacity is exceeded."""
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self._maxsize:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = value

    def contains(self, key):
        """Check whether a key exists in the cache."""
        return key in self._cache

    def remove(self, key):
        """Remove a key from the cache, returning True if it was present."""
        return self._cache.pop(key, None) is not None

    def clear(self):
        """Clear all cached entries and reset hit statistics."""
        self._cache.clear()
        self._hits = 0

    def stats(self):
        """Return current cache size and cumulative hit count."""
        return {"size": len(self._cache), "hits": self._hits}


model_cache = MemoryCache(maxsize=16)
predictions_cache = MemoryCache(maxsize=16)
