class MemoryCache:
    def __init__(self, maxsize=128):
        self._maxsize = maxsize
        self._cache = {}
        self._hits = 0

    def get(self, key):
        if key in self._cache:
            self._hits += 1
            return self._cache[key]
        return None

    def set(self, key, value):
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self._maxsize:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = value

    def contains(self, key):
        return key in self._cache

    def remove(self, key):
        return self._cache.pop(key, None) is not None

    def clear(self):
        self._cache.clear()
        self._hits = 0

    def stats(self):
        return {"size": len(self._cache), "hits": self._hits}


model_cache = MemoryCache(maxsize=16)
predictions_cache = MemoryCache(maxsize=16)
