from __future__ import annotations

import time
from collections import deque


def allow_request(state, client_id: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    limit = int(getattr(state, 'rate_limit_per_minute', 120))
    backend = getattr(state, 'rate_limit_backend', 'memory')

    if backend == 'redis' and getattr(state, 'redis_client', None) is not None:
        redis = state.redis_client
        key = f'rl:{client_id}'
        window_start = now - 60
        redis.zremrangebyscore(key, 0, window_start)
        count = redis.zcard(key)
        if count >= limit:
            return False
        redis.zadd(key, {str(now): now})
        redis.expire(key, 120)
        return True

    # memory fallback
    buckets = getattr(state, 'rate_buckets', None)
    if buckets is None:
        buckets = {}
        state.rate_buckets = buckets

    q = buckets.get(client_id)
    if q is None:
        q = deque()
        buckets[client_id] = q

    window_start = now - 60
    while q and q[0] < window_start:
        q.popleft()

    if len(q) >= limit:
        return False

    q.append(now)
    return True
