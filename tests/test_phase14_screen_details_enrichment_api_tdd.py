from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_screen_details_response_contains_enriched_fields():
    r = client.get('/v1/screens/1450832/fibonacci-based-btw-05-and-0786?page=1&limit=50')
    assert r.status_code == 200
    body = r.json()
    page = body['data']['page']

    assert 'owner_profile_url' in page
    assert 'export_url' in page
    assert 'source_id' in page
    assert 'sort' in page
    assert 'order' in page
    assert 'columns_meta' in page
    assert isinstance(page['columns_meta'], list)
