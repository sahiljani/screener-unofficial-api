from app.core.config import load_settings


def test_phase15_loads_cache_and_retry_settings(monkeypatch):
    monkeypatch.setenv('CACHE_BACKEND', 'redis')
    monkeypatch.setenv('CACHE_TTL_SECONDS', '600')
    monkeypatch.setenv('THROTTLE_COMPANY_INTERVAL_SECONDS', '0.4')
    monkeypatch.setenv('THROTTLE_SECTOR_INTERVAL_SECONDS', '0.7')
    monkeypatch.setenv('THROTTLE_SCREENS_INTERVAL_SECONDS', '1.1')
    monkeypatch.setenv('UPSTREAM_MAX_RETRIES', '4')
    monkeypatch.setenv('UPSTREAM_RETRY_BACKOFF_SECONDS', '0.25')

    s = load_settings()
    assert s.cache_backend == 'redis'
    assert s.cache_ttl_seconds == 600
    assert s.throttle_company_interval_seconds == 0.4
    assert s.throttle_sector_interval_seconds == 0.7
    assert s.throttle_screens_interval_seconds == 1.1
    assert s.upstream_max_retries == 4
    assert s.upstream_retry_backoff_seconds == 0.25


def test_phase15_invalid_cache_backend_falls_back_to_memory(monkeypatch):
    monkeypatch.setenv('CACHE_BACKEND', 'invalid')
    s = load_settings()
    assert s.cache_backend == 'memory'
