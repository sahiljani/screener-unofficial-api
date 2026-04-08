from app.services.screener_client import ScreenerClient


class StubPrewarmClient(ScreenerClient):
    def __init__(self):
        super().__init__()
        self.urls = []

    def _fetch_html(self, url: str, proxy_url: str | None = None) -> str:
        self.urls.append(url)
        if url == 'https://www.screener.in/market/':
            return """
            <html><body>
              <a href='/market/IN06/IN0601/IN060101/'>Pharmaceuticals & Biotechnology</a>
            </body></html>
            """
        return '<html>ok</html>'


def test_prewarm_fetches_known_sector_and_screen_pages():
    c = StubPrewarmClient()

    out = c.prewarm_pages(
        sector_slugs=['pharmaceuticals-biotechnology'],
        screen_refs=[{'screen_id': 1450832, 'slug': 'fibonacci-based-btw-05-and-0786'}],
        pages_per_target=2,
    )

    assert out['data']['attempted_urls'] >= 3
    assert out['data']['warmed_urls'] >= 3
    assert any('/market/' in u for u in c.urls)
    assert any('/screens/1450832/fibonacci-based-btw-05-and-0786/' in u for u in c.urls)
