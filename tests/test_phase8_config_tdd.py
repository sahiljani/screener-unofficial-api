from app.core.config import load_settings


def test_load_settings_from_env(monkeypatch):
    monkeypatch.setenv('API_KEY', 'abc123')
    monkeypatch.setenv('RATE_LIMIT_PER_MINUTE', '77')
    monkeypatch.setenv('RATE_LIMIT_BACKEND', 'redis')
    monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379/0')

    s = load_settings()
    assert s.api_key == 'abc123'
    assert s.rate_limit_per_minute == 77
    assert s.rate_limit_backend == 'redis'
    assert s.redis_url == 'redis://localhost:6379/0'


def test_invalid_backend_falls_back_to_memory(monkeypatch):
    monkeypatch.setenv('RATE_LIMIT_BACKEND', 'invalid-backend')
    s = load_settings()
    assert s.rate_limit_backend == 'memory'
