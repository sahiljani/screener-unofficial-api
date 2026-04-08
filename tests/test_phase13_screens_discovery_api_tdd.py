from fastapi.testclient import TestClient
from app.main import app
import app.api.routes as routes

client = TestClient(app)


def test_screens_pages_endpoint_shape():
    r = client.get('/v1/screens/pages?page=1')
    assert r.status_code == 200
    body = r.json()
    assert 'data' in body
    assert 'page' in body['data']
    assert 'total_pages' in body['data']['page']


def test_list_screens_max_pages_query_shape():
    r = client.get('/v1/screens?page=1&include_all_pages=true&max_pages=2')
    assert r.status_code == 200
    body = r.json()
    assert 'data' in body
    assert 'summary' in body['data']


def test_list_screens_invalid_max_pages_returns_validation_error():
    r = client.get('/v1/screens?page=1&include_all_pages=true&max_pages=0')
    assert r.status_code == 400
    body = r.json()
    assert body['error']['code'] == 'VALIDATION_ERROR'


def test_list_screens_value_error_bubbles_as_bad_request(monkeypatch):
    async def boom(*args, **kwargs):
        raise ValueError('max_pages must be >= 1')

    monkeypatch.setattr(routes.client, 'async_list_screens', boom)
    r = client.get('/v1/screens?page=1&include_all_pages=true&max_pages=1')
    assert r.status_code == 400
    body = r.json()
    assert body['error']['code'] == 'BAD_REQUEST'
