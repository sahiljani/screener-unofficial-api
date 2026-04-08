from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_key_required_when_configured():
    app.state.api_key = "secret123"
    app.state.rate_limit_per_minute = 100
    app.state.rate_buckets = {}

    r = client.get('/v1/ping')
    assert r.status_code == 401
    assert r.json()['error']['code'] == 'AUTH_REQUIRED'

    r2 = client.get('/v1/ping', headers={'x-api-key': 'secret123'})
    assert r2.status_code == 200



def test_rate_limit_blocks_after_threshold():
    app.state.api_key = None
    app.state.rate_limit_per_minute = 2
    app.state.rate_buckets = {}

    r1 = client.get('/v1/ping')
    r2 = client.get('/v1/ping')
    r3 = client.get('/v1/ping')

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.json()['error']['code'] == 'RATE_LIMITED'
