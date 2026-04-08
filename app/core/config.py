from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    api_key: str | None = None
    rate_limit_per_minute: int = 120
    rate_limit_backend: str = 'memory'  # memory|redis
    redis_url: str | None = None


def load_settings() -> Settings:
    api_key = os.getenv('API_KEY')

    rate_limit_raw = os.getenv('RATE_LIMIT_PER_MINUTE', '120')
    try:
        rate_limit_per_minute = max(1, int(rate_limit_raw))
    except ValueError:
        rate_limit_per_minute = 120

    backend = (os.getenv('RATE_LIMIT_BACKEND', 'memory') or 'memory').strip().lower()
    if backend not in {'memory', 'redis'}:
        backend = 'memory'

    redis_url = os.getenv('REDIS_URL')

    return Settings(
        api_key=api_key,
        rate_limit_per_minute=rate_limit_per_minute,
        rate_limit_backend=backend,
        redis_url=redis_url,
    )
