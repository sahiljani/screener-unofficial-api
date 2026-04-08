from __future__ import annotations

import json
import time
from typing import Any


class CacheStore:
    def __init__(self, backend: str = 'memory', redis_client: Any | None = None):
        self.backend = backend
        self.redis_client = redis_client
        self.memory: dict[str, tuple[float, str]] = {}

    def get(self, key: str, now: float | None = None) -> str | None:
        now = time.time() if now is None else now

        if self.backend == 'redis' and self.redis_client is not None:
            raw = self.redis_client.get(key)
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8', errors='ignore')
            return str(raw)

        hit = self.memory.get(key)
        if not hit:
            return None
        expiry, value = hit
        if expiry <= now:
            self.memory.pop(key, None)
            return None
        return value

    def set(self, key: str, value: str, ttl_seconds: int, now: float | None = None) -> None:
        now = time.time() if now is None else now

        if self.backend == 'redis' and self.redis_client is not None:
            self.redis_client.setex(key, int(ttl_seconds), value)
            return

        self.memory[key] = (now + ttl_seconds, value)


class JsonCacheStore(CacheStore):
    def get_json(self, key: str, now: float | None = None) -> Any | None:
        raw = self.get(key, now=now)
        if raw is None:
            return None
        return json.loads(raw)

    def set_json(self, key: str, value: Any, ttl_seconds: int, now: float | None = None) -> None:
        self.set(key, json.dumps(value), ttl_seconds=ttl_seconds, now=now)
