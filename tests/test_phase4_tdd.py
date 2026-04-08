from app.services.screener_client import ScreenerClient


MINIMAL_HTML = """
<html>
  <head><title>TCS share price</title></head>
  <body>
    <ul id='top-ratios'>
      <li><span class='name'>Market Cap</span><span class='value'>100</span></li>
    </ul>
    <section id='analysis'><table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></section>
    <section id='peers'><table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></section>
    <section id='quarters'><table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></section>
    <section id='profit-loss'><table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></section>
    <section id='balance-sheet'><table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></section>
    <section id='cash-flow'><table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></section>
    <section id='ratios'><table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></section>
    <section id='shareholding'><table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></section>
    <section id='documents'><a href='https://example.com/a.pdf'>Doc</a></section>
    <section id='insights'><p>Insight 1</p></section>
  </body>
</html>
"""


class StubClient(ScreenerClient):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def _fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        self.calls += 1
        return MINIMAL_HTML


class StubSitemapClient(ScreenerClient):
    def _fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        if url.endswith('/sitemap.xml'):
            return """
            <sitemapindex>
              <sitemap><loc>https://www.screener.in/sitemap-companies.xml</loc></sitemap>
              <sitemap><loc>https://www.screener.in/sitemap-companies.xml?p=2</loc></sitemap>
            </sitemapindex>
            """
        if 'sitemap-companies.xml?p=2' in url:
            return """
            <urlset>
              <url><loc>https://www.screener.in/company/ABCIND/</loc></url>
              <url><loc>https://www.screener.in/company/ABCTECH/</loc></url>
            </urlset>
            """
        if 'sitemap-companies.xml' in url:
            return """
            <urlset>
              <url><loc>https://www.screener.in/company/XYZ/</loc></url>
            </urlset>
            """
        return ""


def test_company_fetch_uses_cache_for_repeated_requests():
    c = StubClient()
    c.fetch_company('TCS')
    c.fetch_company('TCS')
    assert c.calls == 1


def test_search_companies_scans_company_sitemap_pages_from_index():
    c = StubSitemapClient()
    out = c.search_companies('abc', limit=5)
    symbols = [r['symbol'] for r in out['data']['results']]
    assert 'ABCIND' in symbols
    assert 'ABCTECH' in symbols
