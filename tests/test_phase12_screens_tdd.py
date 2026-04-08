from app.services.screener_client import ScreenerClient

SCREENS_PAGE_1 = """
<html>
  <body>
    <h1>Popular Stock Screens</h1>
    <ul class='items'>
      <li>
        <a href='/screens/1450832/fibonacci-based-btw-05-and-0786/'>
          <strong>Fibonacci based btw 0.5 and 0.786</strong>
          <span class='sub'>Stocks retracement above 0.5 and 0.61 and 0.776</span>
        </a>
      </li>
      <li>
        <a href='/screens/1305506/aditya-joshi/'>
          <strong>ADITYA JOSHI</strong>
          <span class='sub'>MICROCAP MULTIBEGGAR BY PK</span>
        </a>
      </li>
    </ul>
    <div class='pagination'>
      <a href='#'>1</a>
      <a href='?page=2'>2</a>
      <a href='?page=2'>Next</a>
    </div>
  </body>
</html>
"""

SCREENS_PAGE_2 = """
<html>
  <body>
    <h1>Popular Stock Screens</h1>
    <ul class='items'>
      <li>
        <a href='/screens/1233566/zomato/'>
          <strong>Zomato</strong>
          <span class='sub'>Stocks moving to profit</span>
        </a>
      </li>
    </ul>
    <div class='pagination'>
      <a href='?page=1'>1</a>
      <a href='#'>2</a>
    </div>
  </body>
</html>
"""

SCREEN_DETAILS_PAGE_1 = """
<html>
  <body>
    <h1>Fibonacci based btw 0.5 and 0.786</h1>
    <p class='sub'>by Laxman</p>

    <div class='pagination'>
      <a href='#'>1</a>
      <a href='?limit=50&page=2'>2</a>
    </div>

    <p class='sub'>123 results found: Showing page 1 of 2</p>

    <div data-page-results>
      <table class='data-table'>
        <tr><th>S.No.</th><th>Name</th><th>CMP Rs.</th></tr>
        <tr><td>1.</td><td>One Point One</td><td>46.92</td></tr>
        <tr><td>2.</td><td>Stock B</td><td>11.00</td></tr>
      </table>
    </div>

    <textarea id='query-builder'>Current price > 10</textarea>
  </body>
</html>
"""

SCREEN_DETAILS_PAGE_2 = """
<html>
  <body>
    <h1>Fibonacci based btw 0.5 and 0.786</h1>
    <div class='pagination'>
      <a href='?limit=50&page=1'>1</a>
      <a href='#'>2</a>
    </div>
    <div data-page-results>
      <table class='data-table'>
        <tr><th>S.No.</th><th>Name</th><th>CMP Rs.</th></tr>
        <tr><td>3.</td><td>Stock C</td><td>99.00</td></tr>
      </table>
    </div>
    <textarea id='query-builder'>Current price > 10</textarea>
  </body>
</html>
"""


class StubScreensClient(ScreenerClient):
    def _fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        if url == 'https://www.screener.in/screens/?page=1':
            return SCREENS_PAGE_1
        if url == 'https://www.screener.in/screens/?page=2':
            return SCREENS_PAGE_2
        if 'https://www.screener.in/screens/1450832/fibonacci-based-btw-05-and-0786/?page=1' in url:
            return SCREEN_DETAILS_PAGE_1
        if 'https://www.screener.in/screens/1450832/fibonacci-based-btw-05-and-0786/?page=2' in url:
            return SCREEN_DETAILS_PAGE_2
        return ''


def test_list_screens_single_page_shape():
    c = StubScreensClient()
    out = c.list_screens(page=1, include_all_pages=False)

    page = out['data']['page']
    assert page['pagination']['current_page'] == 1
    assert page['pagination']['total_pages'] == 2
    assert page['item_count'] == 2
    assert page['items'][0]['screen_id'] == 1450832


def test_list_screens_all_pages_shape():
    c = StubScreensClient()
    out = c.list_screens(page=1, include_all_pages=True)

    assert len(out['data']['pages']) == 2
    assert out['data']['summary']['pages_fetched'] == 2
    assert out['data']['summary']['screens_fetched'] == 3


def test_screen_details_single_page_shape():
    c = StubScreensClient()
    out = c.fetch_screen_details(
        screen_id=1450832,
        slug='fibonacci-based-btw-05-and-0786',
        page=1,
        limit=50,
        include_all_pages=False,
    )

    page = out['data']['page']
    assert page['title'] == 'Fibonacci based btw 0.5 and 0.786'
    assert page['author'] == 'Laxman'
    assert page['query'] == 'Current price > 10'
    assert page['pagination']['total_pages'] == 2
    assert len(page['rows']) == 2


def test_screen_details_all_pages_shape():
    c = StubScreensClient()
    out = c.fetch_screen_details(
        screen_id=1450832,
        slug='fibonacci-based-btw-05-and-0786',
        page=1,
        limit=50,
        include_all_pages=True,
    )

    assert len(out['data']['pages']) == 2
    assert out['data']['summary']['pages_fetched'] == 2
    assert out['data']['summary']['rows_fetched'] == 3
