from app.core.cache import CacheStore


class FakeRedis:
    def __init__(self):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def setex(self, key, ttl, value):
        self._store[key] = value
        return True


def test_memory_cache_store_respects_ttl():
    cache = CacheStore(backend='memory')
    cache.set('k1', 'value-1', ttl_seconds=10, now=100.0)

    assert cache.get('k1', now=105.0) == 'value-1'
    assert cache.get('k1', now=111.0) is None


def test_redis_cache_store_uses_redis_client():
    redis = FakeRedis()
    cache = CacheStore(backend='redis', redis_client=redis)

    cache.set('k2', 'value-2', ttl_seconds=60)
    assert cache.get('k2') == 'value-2'
