from app.services.screener_client import ScreenerClient


SCREENS_PAGE = """
<html>
  <body>
    <h1>Popular Stock Screens</h1>
    <ul class='items'>
      <li><a href='/screens/1/a/'><strong>A</strong><span class='sub'>Desc</span></a></li>
    </ul>
    <div class='pagination'><a href='#'>1</a></div>
  </body>
</html>
"""


class StubFiltersClient(ScreenerClient):
    def _fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        if url == 'https://www.screener.in/screens/?page=1':
            return SCREENS_PAGE
        return ''


def test_filters_placeholder_is_echoed_and_not_applied():
    c = StubFiltersClient()
    out = c.list_screens(page=1, filters='author:demo', include_all_pages=False)

    filters = out['data']['filters']
    assert filters['raw'] == 'author:demo'
    assert filters['applied'] is False
    assert 'placeholder' in filters['note'].lower()
