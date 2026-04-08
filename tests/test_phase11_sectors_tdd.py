from app.services.screener_client import ScreenerClient

MARKET_OVERVIEW_HTML = """
<html>
  <body>
    <a href='/market/IN07/IN0702/IN070201/IN070201001/'>Aerospace & Defense</a>
    <a href='/market/IN04/IN0401/IN040104/IN040104003/'>Other Food Products</a>
    <a href='/market/IN06/IN0601/IN060101/'>Pharmaceuticals & Biotechnology</a>
  </body>
</html>
"""

SECTOR_PAGE_1_HTML = """
<html>
  <body>
    <h1>Pharmaceuticals & Biotechnology Companies</h1>
    <p class='sub'>223 results found: Showing page 1 of 2</p>

    <div class='pagination'>
      <a href='#'>1</a>
      <a href='?limit=50&page=2'>2</a>
      <a href='?limit=50&page=2'>Next</a>
    </div>

    <p class='sub'>
      <a href='/market/IN06/'>Healthcare</a>
      <a href='/market/IN06/IN0601/'>Pharmaceuticals & Biotechnology</a>
    </p>

    <div data-page-results>
      <table class='data-table'>
        <tr><th>S.No.</th><th>Name</th><th>CMP Rs.</th></tr>
        <tr><td>1.</td><td>Sun Pharma.Inds.</td><td>1718.00</td></tr>
        <tr><td>2.</td><td>Divi's Lab.</td><td>5850.00</td></tr>
      </table>
    </div>
  </body>
</html>
"""

SECTOR_PAGE_2_HTML = """
<html>
  <body>
    <h1>Pharmaceuticals & Biotechnology Companies</h1>
    <p class='sub'>223 results found: Showing page 2 of 2</p>

    <div class='pagination'>
      <a href='?limit=50&page=1'>1</a>
      <a href='#'>2</a>
    </div>

    <div data-page-results>
      <table class='data-table'>
        <tr><th>S.No.</th><th>Name</th><th>CMP Rs.</th></tr>
        <tr><td>3.</td><td>Torrent Pharma.</td><td>4051.30</td></tr>
      </table>
    </div>
  </body>
</html>
"""


class StubSectorClient(ScreenerClient):
    def _fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        if url == 'https://www.screener.in/market/':
            return MARKET_OVERVIEW_HTML
        if 'IN060101/?limit=50&page=1' in url:
            return SECTOR_PAGE_1_HTML
        if 'IN060101/?limit=50&page=2' in url:
            return SECTOR_PAGE_2_HTML
        return ""


def test_list_sectors_includes_requested_aliases():
    c = StubSectorClient()
    out = c.list_sectors()

    sectors = out['data']['sectors']
    names = {s['name']: s for s in sectors}

    assert 'Aerospace & Defense' in names
    assert names['Aerospace & Defense']['available'] is True

    assert 'Pharmaceuticals & Biotechnology' in names
    assert names['Pharmaceuticals & Biotechnology']['available'] is True


def test_fetch_sector_page_returns_structured_table_and_pagination():
    c = StubSectorClient()
    out = c.fetch_sector_data('pharmaceuticals-biotechnology', page=1, limit=50, include_all_pages=False)

    data = out['data']
    assert data['sector'] == 'Pharmaceuticals & Biotechnology'
    assert data['slug'] == 'pharmaceuticals-biotechnology'

    page = data['page']
    assert page['pagination']['current_page'] == 1
    assert page['pagination']['total_pages'] == 2
    assert page['total_results'] == 223
    assert page['columns'] == ['S.No.', 'Name', 'CMP Rs.']
    assert len(page['rows']) == 2


def test_fetch_sector_all_pages_aggregates_rows():
    c = StubSectorClient()
    out = c.fetch_sector_data('pharmaceuticals-biotechnology', page=1, limit=50, include_all_pages=True)

    data = out['data']
    assert len(data['pages']) == 2
    assert data['summary']['pages_fetched'] == 2
    assert data['summary']['rows_fetched'] == 3
