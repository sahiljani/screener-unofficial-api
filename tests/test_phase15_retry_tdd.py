import httpx

from app.services.screener_client import ScreenerClient


def _status_error(code: int) -> httpx.HTTPStatusError:
    req = httpx.Request('GET', 'https://www.screener.in/company/TCS/')
    res = httpx.Response(code, request=req)
    return httpx.HTTPStatusError(f'status {code}', request=req, response=res)


class RetryHarness(ScreenerClient):
    def __init__(self, errors_then_success):
        super().__init__(upstream_max_retries=3, upstream_retry_backoff_seconds=0)
        self.errors_then_success = list(errors_then_success)
        self.calls = 0

    def _throttle_for_scope(self, scope: str) -> None:
        return

    def _http_get_once(self, url: str, proxy_url: str | None = None) -> str:
        self.calls += 1
        if self.errors_then_success:
            nxt = self.errors_then_success.pop(0)
            if isinstance(nxt, Exception):
                raise nxt
        return '<html>ok</html>'


def test_retry_succeeds_after_transient_429_then_502():
    c = RetryHarness([_status_error(429), _status_error(502)])
    out = c._fetch_html('https://www.screener.in/company/TCS/')
    assert out == '<html>ok</html>'
    assert c.calls == 3


def test_retry_stops_on_non_retryable_status():
    c = RetryHarness([_status_error(404)])
    try:
        c._fetch_html('https://www.screener.in/company/TCS/')
        assert False, 'Expected HTTPStatusError'
    except httpx.HTTPStatusError as exc:
        assert exc.response.status_code == 404
    assert c.calls == 1
