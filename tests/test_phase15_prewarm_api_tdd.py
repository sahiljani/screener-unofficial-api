from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_prewarm_endpoint_shape():
    r = client.post(
        '/v1/prewarm',
        json={
            'sector_slugs': ['pharmaceuticals-biotechnology'],
            'screen_refs': [{'screen_id': 1450832, 'slug': 'fibonacci-based-btw-05-and-0786'}],
            'pages_per_target': 1,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert 'data' in body
    assert 'attempted_urls' in body['data']
    assert 'warmed_urls' in body['data']
