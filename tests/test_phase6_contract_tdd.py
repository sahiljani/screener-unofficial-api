from fastapi.testclient import TestClient
import app.api.routes as routes
from app.main import app

client = TestClient(app)


def test_validation_errors_are_normalized_to_400():
    r = client.get('/v1/company/TCS?mode=bad')
    assert r.status_code == 400
    body = r.json()
    assert body['error']['code'] == 'VALIDATION_ERROR'
    assert 'detail' in body


def test_http_errors_include_error_envelope():
    r = client.get('/v1/company/TCS/not-a-valid-tab')
    assert r.status_code == 400
    body = r.json()
    assert body['error']['code'] == 'BAD_REQUEST'
    assert 'Unsupported tab' in body['error']['message']


def test_unhandled_errors_are_normalized_to_502(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError('upstream down')

    monkeypatch.setattr(routes.client, 'search_companies', boom)
    r = client.get('/v1/search/companies?q=tata')
    assert r.status_code == 502
    body = r.json()
    assert body['error']['code'] == 'UPSTREAM_ERROR'
    assert 'upstream down' in body['error']['message']
