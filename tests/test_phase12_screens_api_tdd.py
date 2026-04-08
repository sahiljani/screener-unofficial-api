from fastapi.testclient import TestClient
from app.main import app
import app.api.routes as routes

client = TestClient(app)


def test_list_screens_endpoint_shape():
    r = client.get('/v1/screens?page=1')
    assert r.status_code == 200
    body = r.json()
    assert 'data' in body
    assert 'page' in body['data']
    assert 'items' in body['data']['page']


def test_list_screens_all_pages_endpoint_shape():
    r = client.get('/v1/screens?page=1&include_all_pages=true')
    assert r.status_code == 200
    body = r.json()
    assert 'data' in body
    assert 'pages' in body['data']


def test_screen_details_endpoint_shape():
    r = client.get('/v1/screens/1450832/fibonacci-based-btw-05-and-0786?page=1&limit=50')
    assert r.status_code == 200
    body = r.json()
    assert 'data' in body
    assert 'page' in body['data']
    assert 'query' in body['data']['page']


def test_screen_details_returns_400_for_invalid(monkeypatch):
    async def boom(*args, **kwargs):
        raise ValueError('Screen not found')

    monkeypatch.setattr(routes.client, 'async_fetch_screen_details', boom)
    r = client.get('/v1/screens/9999999/not-found')
    assert r.status_code == 400
    body = r.json()
    assert body['error']['code'] == 'BAD_REQUEST'
