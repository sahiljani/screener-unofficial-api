from app.services.screener_client import ScreenerClient

SCREENS_PAGE_50 = """
<html>
  <body>
    <h1>Popular Stock Screens</h1>
    <ul class='items'>
      <li>
        <a href='/screens/500001/screen-a/'>
          <strong>Screen A</strong>
          <span class='sub'>Desc A</span>
        </a>
      </li>
    </ul>
    <div class='pagination'>
      <a href='?page=49'>Previous</a>
      <a href='?page=47'>47</a>
      <a href='?page=48'>48</a>
      <a href='?page=49'>49</a>
      <a href='#'>50</a>
    </div>
  </body>
</html>
"""

SCREENS_PAGE_1_DUP = """
<html>
  <body>
    <h1>Popular Stock Screens</h1>
    <ul class='items'>
      <li><a href='/screens/111111/alpha/'><strong>Alpha</strong><span class='sub'>A</span></a></li>
      <li><a href='/screens/222222/beta/'><strong>Beta</strong><span class='sub'>B</span></a></li>
    </ul>
    <div class='pagination'>
      <a href='#'>1</a>
      <a href='?page=2'>2</a>
      <a href='?page=3'>3</a>
      <a href='?page=4'>4</a>
    </div>
  </body>
</html>
"""

SCREENS_PAGE_2_DUP = """
<html>
  <body>
    <h1>Popular Stock Screens</h1>
    <ul class='items'>
      <li><a href='/screens/222222/beta/'><strong>Beta</strong><span class='sub'>B</span></a></li>
      <li><a href='/screens/333333/gamma/'><strong>Gamma</strong><span class='sub'>C</span></a></li>
    </ul>
    <div class='pagination'>
      <a href='?page=1'>1</a>
      <a href='#'>2</a>
      <a href='?page=3'>3</a>
      <a href='?page=4'>4</a>
    </div>
  </body>
</html>
"""

SCREENS_PAGE_3_DUP = """
<html>
  <body>
    <h1>Popular Stock Screens</h1>
    <ul class='items'>
      <li><a href='/screens/444444/delta/'><strong>Delta</strong><span class='sub'>D</span></a></li>
    </ul>
    <div class='pagination'>
      <a href='?page=1'>1</a>
      <a href='?page=2'>2</a>
      <a href='#'>3</a>
      <a href='?page=4'>4</a>
    </div>
  </body>
</html>
"""


class StubPhase13Client(ScreenerClient):
    def _fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        if url == 'https://www.screener.in/screens/?page=50':
            return SCREENS_PAGE_50
        if url == 'https://www.screener.in/screens/?page=1':
            return SCREENS_PAGE_1_DUP
        if url == 'https://www.screener.in/screens/?page=2':
            return SCREENS_PAGE_2_DUP
        if url == 'https://www.screener.in/screens/?page=3':
            return SCREENS_PAGE_3_DUP
        if url == 'https://www.screener.in/screens/?page=4':
            # sparse/no-next style final page
            return """
            <html><body>
              <h1>Popular Stock Screens</h1>
              <ul class='items'></ul>
              <div class='pagination'><a href='?page=3'>3</a><a href='#'>4</a></div>
            </body></html>
            """
        return ''


def test_screens_pages_endpoint_data_handles_page_50():
    c = StubPhase13Client()
    out = c.screens_pages(page=50)

    page = out['data']['page']
    assert page['current_page'] == 50
    assert page['total_pages'] == 50
    assert page['screens_on_page'] == 1


def test_list_screens_all_pages_dedupes_by_screen_id():
    c = StubPhase13Client()
    out = c.list_screens(page=1, include_all_pages=True)

    summary = out['data']['summary']
    assert summary['pages_fetched'] == 4
    assert summary['duplicates_skipped'] == 1
    assert summary['screens_fetched'] == 4


def test_list_screens_all_pages_honors_max_pages_cap():
    c = StubPhase13Client()
    out = c.list_screens(page=1, include_all_pages=True, max_pages=2)

    summary = out['data']['summary']
    assert summary['from_page'] == 1
    assert summary['to_page'] == 2
    assert summary['pages_fetched'] == 2
    assert summary['max_pages_applied'] is True
