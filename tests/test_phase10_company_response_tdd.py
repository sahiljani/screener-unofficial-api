from app.services.screener_client import ScreenerClient


HTML_WITH_DYNAMIC_PEERS = """
<html>
  <head><title>TCS share price</title></head>
  <body>
    <div id='company-info' data-company-id='3365' data-warehouse-id='6599230'></div>
    <ul id='top-ratios'>
      <li><span class='name'>Market Cap</span><span class='value'>100</span></li>
    </ul>

    <section id='analysis'>
      <div class='pros'><ul><li>High ROE</li><li>Healthy cash flows</li></ul></div>
      <div class='cons'><ul><li>Rich valuation</li></ul></div>
      <p class='sub'>Pros / cons are machine generated.</p>
    </section>

    <section id='peers'>
      <div id='peers-table-placeholder'>Loading peers table ...</div>
    </section>

    <section id='quarters'><table><tr><th>A</th></tr><tr><td>1</td></tr></table></section>
    <section id='profit-loss'><table><tr><th>A</th></tr><tr><td>1</td></tr></table></section>
    <section id='balance-sheet'><table><tr><th>A</th></tr><tr><td>1</td></tr></table></section>
    <section id='cash-flow'><table><tr><th>A</th></tr><tr><td>1</td></tr></table></section>
    <section id='ratios'><table><tr><th>A</th></tr><tr><td>1</td></tr></table></section>
    <section id='shareholding'><table><tr><th>A</th></tr><tr><td>1</td></tr></table></section>
    <section id='documents'><a href='https://example.com/a.pdf'>Doc</a></section>
  </body>
</html>
"""

PEERS_FRAGMENT = """
<div class='responsive-holder'>
  <table>
    <tr><th>S.No.</th><th>Name</th><th>CMP Rs.</th></tr>
    <tr><td>1</td><td>TCS</td><td>100</td></tr>
    <tr><td>2</td><td>INFY</td><td>200</td></tr>
  </table>
</div>
"""


class DynamicPeersStub(ScreenerClient):
    def _fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        if '/api/company/' in url and '/peers/' in url:
            return PEERS_FRAGMENT
        return HTML_WITH_DYNAMIC_PEERS


def test_company_aggregate_excludes_insights_and_populates_analysis_and_peers():
    c = DynamicPeersStub()
    out = c.fetch_company('TCS')

    data = out['data']
    assert 'insights' not in data

    analysis = data['analysis']
    assert isinstance(analysis['pros'], list)
    assert isinstance(analysis['cons'], list)
    assert len(analysis['pros']) > 0
    assert len(analysis['cons']) > 0

    peers = data['peers']
    assert isinstance(peers['columns'], list)
    assert isinstance(peers['rows'], list)
    assert len(peers['columns']) > 0
    assert len(peers['rows']) > 0


def test_analysis_tab_returns_structured_non_empty_data():
    c = DynamicPeersStub()
    out = c.fetch_company_tab('TCS', tab='analysis')
    result = out['data']['result']

    assert isinstance(result['pros'], list)
    assert isinstance(result['cons'], list)
    assert len(result['pros']) > 0


def test_peers_tab_returns_structured_non_empty_data():
    c = DynamicPeersStub()
    out = c.fetch_company_tab('TCS', tab='peers')
    result = out['data']['result']

    assert isinstance(result['columns'], list)
    assert isinstance(result['rows'], list)
    assert len(result['columns']) > 0
    assert len(result['rows']) > 0
