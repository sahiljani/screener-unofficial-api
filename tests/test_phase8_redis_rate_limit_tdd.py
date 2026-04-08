from types import SimpleNamespace

from app.core.rate_limit import allow_request


class FakeRedis:
    def __init__(self):
        self._zsets = {}

    def zremrangebyscore(self, key, min_score, max_score):
        rows = self._zsets.get(key, [])
        self._zsets[key] = [(m, s) for (m, s) in rows if not (min_score <= s <= max_score)]

    def zcard(self, key):
        return len(self._zsets.get(key, []))

    def zadd(self, key, mapping):
        rows = self._zsets.setdefault(key, [])
        for member, score in mapping.items():
            rows.append((member, float(score)))

    def expire(self, key, ttl):
        return True


def test_redis_backend_rate_limit_enforced():
    state = SimpleNamespace(
        rate_limit_per_minute=2,
        rate_limit_backend='redis',
        redis_client=FakeRedis(),
        rate_buckets={},
    )

    assert allow_request(state, 'user-1', now=1000.0)
    assert allow_request(state, 'user-1', now=1000.1)
    assert not allow_request(state, 'user-1', now=1000.2)
