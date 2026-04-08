from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ready_is_ok_for_memory_backend():
    app.state.rate_limit_backend = 'memory'
    app.state.redis_client = None

    r = client.get('/ready')
    assert r.status_code == 200
    body = r.json()
    assert body['ok'] is True
    assert body['checks']['rate_limit_backend'] == 'memory'


def test_ready_fails_when_redis_backend_has_no_client():
    app.state.rate_limit_backend = 'redis'
    app.state.redis_client = None

    r = client.get('/ready')
    assert r.status_code == 503
    body = r.json()
    assert body['ok'] is False
    assert body['checks']['redis'] == 'missing_client'
