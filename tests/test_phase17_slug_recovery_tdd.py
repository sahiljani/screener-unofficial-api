from app.services.screener_client import ScreenerClient


SCREENS_PAGE = """
<html>
  <body>
    <h1>Popular Stock Screens</h1>
    <ul class='items'>
      <li><a href='/screens/1450832/new-slug/'><strong>Screen</strong><span class='sub'>Desc</span></a></li>
    </ul>
    <div class='pagination'><a href='#'>1</a></div>
  </body>
</html>
"""

REGISTER_PAGE = """
<html><body><h1>Register</h1></body></html>
"""

VALID_SCREEN_PAGE = """
<html>
  <body>
    <h1>Screen title</h1>
    <p class='sub'>by Demo</p>
    <div class='pagination'><a href='#'>1</a></div>
    <div data-page-results>
      <table class='data-table'>
        <tr><th>S.No.</th><th>Name</th></tr>
        <tr><td>1.</td><td>ABC</td></tr>
      </table>
    </div>
    <textarea id='query-builder'>Current price > 10</textarea>
  </body>
</html>
"""


class StubSlugRecoveryClient(ScreenerClient):
    def _fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        if url == 'https://www.screener.in/screens/?page=1':
            return SCREENS_PAGE
        if 'https://www.screener.in/screens/1450832/old-slug/' in url:
            return REGISTER_PAGE
        if 'https://www.screener.in/screens/1450832/new-slug/' in url:
            return VALID_SCREEN_PAGE
        return ''


def test_fetch_screen_details_recovers_from_stale_slug():
    c = StubSlugRecoveryClient()
    out = c.fetch_screen_details(screen_id=1450832, slug='old-slug', page=1, limit=50)

    assert out['data']['slug'] == 'new-slug'
    assert out['data']['page']['title'] == 'Screen title'
    assert out['data']['page']['row_count'] == 1
