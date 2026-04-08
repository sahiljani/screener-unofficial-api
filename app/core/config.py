from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    api_key: str | None = None
    rate_limit_per_minute: int = 120
    rate_limit_backend: str = 'memory'  # memory|redis
    redis_url: str | None = None

    cache_backend: str = 'memory'  # memory|redis
    cache_ttl_seconds: int = 300

    throttle_company_interval_seconds: float = 0.2
    throttle_sector_interval_seconds: float = 0.2
    throttle_screens_interval_seconds: float = 0.2

    upstream_max_retries: int = 2
    upstream_retry_backoff_seconds: float = 0.5

    screens_max_pages_default: int = 20
    max_crawl_seconds: float = 60.0


def _parse_int(value: str | None, default: int, minimum: int | None = None) -> int:
    try:
        out = int(value) if value is not None else default
    except ValueError:
        out = default
    if minimum is not None:
        out = max(minimum, out)
    return out


def _parse_float(value: str | None, default: float, minimum: float | None = None) -> float:
    try:
        out = float(value) if value is not None else default
    except ValueError:
        out = default
    if minimum is not None:
        out = max(minimum, out)
    return out


def load_settings() -> Settings:
    api_key = os.getenv('API_KEY')

    rate_limit_per_minute = _parse_int(os.getenv('RATE_LIMIT_PER_MINUTE', '120'), 120, minimum=1)

    backend = (os.getenv('RATE_LIMIT_BACKEND', 'memory') or 'memory').strip().lower()
    if backend not in {'memory', 'redis'}:
        backend = 'memory'

    redis_url = os.getenv('REDIS_URL')

    cache_backend = (os.getenv('CACHE_BACKEND', 'memory') or 'memory').strip().lower()
    if cache_backend not in {'memory', 'redis'}:
        cache_backend = 'memory'

    cache_ttl_seconds = _parse_int(os.getenv('CACHE_TTL_SECONDS', '300'), 300, minimum=1)

    throttle_company_interval_seconds = _parse_float(os.getenv('THROTTLE_COMPANY_INTERVAL_SECONDS', '0.2'), 0.2, minimum=0.0)
    throttle_sector_interval_seconds = _parse_float(os.getenv('THROTTLE_SECTOR_INTERVAL_SECONDS', '0.2'), 0.2, minimum=0.0)
    throttle_screens_interval_seconds = _parse_float(os.getenv('THROTTLE_SCREENS_INTERVAL_SECONDS', '0.2'), 0.2, minimum=0.0)

    upstream_max_retries = _parse_int(os.getenv('UPSTREAM_MAX_RETRIES', '2'), 2, minimum=0)
    upstream_retry_backoff_seconds = _parse_float(os.getenv('UPSTREAM_RETRY_BACKOFF_SECONDS', '0.5'), 0.5, minimum=0.0)

    screens_max_pages_default = _parse_int(os.getenv('SCREENS_MAX_PAGES_DEFAULT', '20'), 20, minimum=1)
    max_crawl_seconds = _parse_float(os.getenv('MAX_CRAWL_SECONDS', '60.0'), 60.0, minimum=5.0)

    return Settings(
        api_key=api_key,
        rate_limit_per_minute=rate_limit_per_minute,
        rate_limit_backend=backend,
        redis_url=redis_url,
        cache_backend=cache_backend,
        cache_ttl_seconds=cache_ttl_seconds,
        throttle_company_interval_seconds=throttle_company_interval_seconds,
        throttle_sector_interval_seconds=throttle_sector_interval_seconds,
        throttle_screens_interval_seconds=throttle_screens_interval_seconds,
        upstream_max_retries=upstream_max_retries,
        upstream_retry_backoff_seconds=upstream_retry_backoff_seconds,
        screens_max_pages_default=screens_max_pages_default,
        max_crawl_seconds=max_crawl_seconds,
    )
