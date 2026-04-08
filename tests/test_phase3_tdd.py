from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_raw_endpoint_returns_html_shape():
    r = client.get('/v1/company/TCS/raw')
    assert r.status_code == 200
    body = r.json()
    assert body['data']['symbol'] == 'TCS'
    assert body['data']['mode'] == 'consolidated'
    assert 'html' in body['data']
    assert isinstance(body['data']['html'], str)
    assert len(body['data']['html']) > 1000
    assert 'sections' in body['data']
    assert isinstance(body['data']['sections'], list)


def test_compare_endpoint_for_two_symbols():
    r = client.get('/v1/compare?symbols=TCS,INFY')
    assert r.status_code == 200
    body = r.json()
    assert 'data' in body
    assert 'comparisons' in body['data']
    assert isinstance(body['data']['comparisons'], list)
    assert len(body['data']['comparisons']) == 2


def test_search_companies_endpoint_shape():
    r = client.get('/v1/search/companies?q=tata&limit=5')
    assert r.status_code == 200
    body = r.json()
    assert 'data' in body
    assert 'query' in body['data']
    assert body['data']['query'] == 'tata'
    assert 'results' in body['data']
    assert isinstance(body['data']['results'], list)
