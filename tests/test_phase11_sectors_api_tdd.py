from fastapi.testclient import TestClient
from app.main import app
import app.api.routes as routes

client = TestClient(app)


def test_list_sectors_endpoint_shape():
    r = client.get('/v1/sectors')
    assert r.status_code == 200
    body = r.json()
    assert 'data' in body
    assert 'sectors' in body['data']
    assert isinstance(body['data']['sectors'], list)


def test_sector_data_endpoint_shape():
    r = client.get('/v1/sectors/pharmaceuticals-biotechnology?limit=50&page=1')
    assert r.status_code == 200
    body = r.json()
    assert 'data' in body
    assert 'page' in body['data']
    assert 'columns' in body['data']['page']
    assert 'rows' in body['data']['page']


def test_sector_data_endpoint_supports_all_pages_flag():
    r = client.get('/v1/sectors/pharmaceuticals-biotechnology?limit=50&page=1&include_all_pages=true')
    assert r.status_code == 200
    body = r.json()
    assert 'pages' in body['data']
    assert isinstance(body['data']['pages'], list)


def test_sector_data_endpoint_returns_400_for_unknown_sector(monkeypatch):
    def boom(*args, **kwargs):
        raise ValueError('Unknown sector')

    monkeypatch.setattr(routes.client, 'fetch_sector_data', boom)
    r = client.get('/v1/sectors/unknown-sector')
    assert r.status_code == 400
    body = r.json()
    assert body['error']['code'] == 'BAD_REQUEST'
