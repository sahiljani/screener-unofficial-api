from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_openapi_contains_examples_for_phase16_endpoints():
    r = client.get('/openapi.json')
    assert r.status_code == 200
    spec = r.json()

    assert '/v1/sectors' in spec['paths']
    assert '/v1/sectors/{sector}' in spec['paths']
    assert '/v1/screens' in spec['paths']
    assert '/v1/screens/{screen_id}/{slug}' in spec['paths']

    screens_get = spec['paths']['/v1/screens']['get']
    assert 'examples' in screens_get
