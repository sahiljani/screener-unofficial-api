from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_rejects_unsupported_tab():
    r = client.get('/v1/company/TCS/not-a-tab')
    assert r.status_code == 400
    assert 'Unsupported tab' in r.json()['detail']


def test_profit_loss_tab_returns_table_shape():
    r = client.get('/v1/company/TCS/profit-loss')
    assert r.status_code == 200
    body = r.json()
    assert body['data']['tab'] == 'profit-loss'
    assert 'columns' in body['data']['result']
    assert 'rows' in body['data']['result']
    assert isinstance(body['data']['result']['columns'], list)
    assert isinstance(body['data']['result']['rows'], list)


def test_balance_sheet_tab_returns_table_shape():
    r = client.get('/v1/company/TCS/balance-sheet')
    assert r.status_code == 200
    body = r.json()
    assert body['data']['tab'] == 'balance-sheet'
    assert 'columns' in body['data']['result']
    assert 'rows' in body['data']['result']


def test_cash_flow_tab_returns_table_shape():
    r = client.get('/v1/company/TCS/cash-flow')
    assert r.status_code == 200
    body = r.json()
    assert body['data']['tab'] == 'cash-flow'
    assert 'columns' in body['data']['result']
    assert 'rows' in body['data']['result']


def test_ratios_tab_returns_table_shape():
    r = client.get('/v1/company/TCS/ratios')
    assert r.status_code == 200
    body = r.json()
    assert body['data']['tab'] == 'ratios'
    assert 'columns' in body['data']['result']
    assert 'rows' in body['data']['result']


def test_shareholding_tab_returns_table_shape():
    r = client.get('/v1/company/TCS/shareholding')
    assert r.status_code == 200
    body = r.json()
    assert body['data']['tab'] == 'shareholding'
    assert 'columns' in body['data']['result']
    assert 'rows' in body['data']['result']


def test_documents_tab_returns_links_shape():
    r = client.get('/v1/company/TCS/documents')
    assert r.status_code == 200
    body = r.json()
    assert body['data']['tab'] == 'documents'
    assert 'links' in body['data']['result']
    assert isinstance(body['data']['result']['links'], list)


def test_analysis_tab_returns_structured_shape():
    r = client.get('/v1/company/TCS/analysis')
    assert r.status_code == 200
    body = r.json()
    assert body['data']['tab'] == 'analysis'
    assert 'pros' in body['data']['result']
    assert 'cons' in body['data']['result']
    assert 'notes' in body['data']['result']
    assert isinstance(body['data']['result']['pros'], list)
    assert isinstance(body['data']['result']['cons'], list)


def test_peers_tab_returns_structured_shape():
    r = client.get('/v1/company/TCS/peers')
    assert r.status_code == 200
    body = r.json()
    assert body['data']['tab'] == 'peers'
    assert 'columns' in body['data']['result']
    assert 'rows' in body['data']['result']
    assert isinstance(body['data']['result']['columns'], list)
    assert isinstance(body['data']['result']['rows'], list)


def test_company_aggregate_contains_major_sections_without_insights():
    r = client.get('/v1/company/TCS')
    assert r.status_code == 200
    data = r.json()['data']
    assert 'analysis' in data
    assert 'peers' in data
    assert 'profit_loss' in data
    assert 'balance_sheet' in data
    assert 'cash_flow' in data
    assert 'ratios' in data
    assert 'shareholding' in data
    assert 'documents' in data
    assert 'insights' not in data
