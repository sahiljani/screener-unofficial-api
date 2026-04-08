from app.services.screener_client import ScreenerClient

SCREEN_DETAILS_ENRICHED = """
<html>
  <body>
    <h1>Quality Growth</h1>
    <p class='sub'>by <a href='/user/demo/'>Demo User</a></p>

    <form action='/api/export/screen/?url_name=screen&screen_id=777&slug_name=quality-growth' method='POST'></form>

    <input type='hidden' name='source_id' value='777' id='id_source_id'>
    <input type='hidden' name='sort' value='current price' id='id_sort'>
    <input type='hidden' name='order' value='asc' id='id_order'>

    <div class='pagination'>
      <a href='#'>1</a>
    </div>

    <div data-page-results>
      <table class='data-table'>
        <tr>
          <th>S.No.</th>
          <th>Name</th>
          <th data-tooltip='Current Price'>CMP <span>Rs.</span></th>
        </tr>
        <tr><td>1.</td><td>ABC</td><td>100</td></tr>
      </table>
    </div>

    <textarea id='query-builder'>Current price > 50</textarea>
  </body>
</html>
"""


class StubPhase14Client(ScreenerClient):
    def _fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        if 'https://www.screener.in/screens/777/quality-growth/?limit=50&page=1' in url:
            return SCREEN_DETAILS_ENRICHED
        return ''


def test_screen_details_enriched_metadata_is_extracted():
    c = StubPhase14Client()
    out = c.fetch_screen_details(screen_id=777, slug='quality-growth', page=1, limit=50)

    page = out['data']['page']
    assert page['author'] == 'Demo User'
    assert page['owner_profile_url'] == 'https://www.screener.in/user/demo/'
    assert page['export_url'] == 'https://www.screener.in/api/export/screen/?url_name=screen&screen_id=777&slug_name=quality-growth'
    assert page['source_id'] == '777'
    assert page['sort'] == 'current price'
    assert page['order'] == 'asc'

    cols_meta = page['columns_meta']
    assert isinstance(cols_meta, list)
    assert cols_meta[2]['name'] == 'CMP Rs.'
    assert cols_meta[2]['tooltip'] == 'Current Price'
    assert cols_meta[2]['unit'] == 'Rs.'
