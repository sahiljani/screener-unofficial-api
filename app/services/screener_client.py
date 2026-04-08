from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import time

import httpx
from selectolax.parser import HTMLParser

BASE = "https://www.screener.in"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

TAB_TO_SECTION_ID = {
    "analysis": "analysis",
    "peers": "peers",
    "quarters": "quarters",
    "profit-loss": "profit-loss",
    "balance-sheet": "balance-sheet",
    "cash-flow": "cash-flow",
    "ratios": "ratios",
    "shareholding": "shareholding",
}


class ScreenerClient:
    def __init__(self, cache_ttl_seconds: int = 300, min_interval_seconds: float = 0.2):
        self.cache_ttl_seconds = cache_ttl_seconds
        self.min_interval_seconds = min_interval_seconds
        self._cache: dict[str, tuple[float, str]] = {}
        self._last_request_at = 0.0

    def _url(self, symbol: str, mode: str) -> str:
        s = symbol.strip().upper()
        if mode == "consolidated":
            return f"{BASE}/company/{s}/consolidated/"
        return f"{BASE}/company/{s}/"

    def _cache_key(self, url: str, proxy_url: str | None = None) -> str:
        return f"{proxy_url or 'direct'}::{url}"

    def _throttle(self) -> None:
        now = time.time()
        wait_for = self.min_interval_seconds - (now - self._last_request_at)
        if wait_for > 0:
            time.sleep(wait_for)
        self._last_request_at = time.time()

    def _fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        self._throttle()
        with httpx.Client(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": UA},
            proxy=proxy_url if proxy_url else None,
        ) as c:
            r = c.get(url)
            r.raise_for_status()
            return r.text

    def _fetch_html(self, url: str, proxy_url: str | None = None) -> str:
        key = self._cache_key(url, proxy_url)
        now = time.time()
        hit = self._cache.get(key)
        if hit and hit[0] > now:
            return hit[1]

        html = self._fetch_html_raw(url, proxy_url=proxy_url)
        self._cache[key] = (now + self.cache_ttl_seconds, html)
        return html


    def _meta(self, url: str, proxy_url: str | None, parser_version: str = "0.4.0") -> dict[str, Any]:
        return {
            "source_url": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "parser_version": parser_version,
            "proxy_used": bool(proxy_url),
        }

    def _extract_overview(self, tree: HTMLParser) -> dict[str, Any]:
        title = tree.css_first("title")
        company_name = title.text().split(" share price", 1)[0].strip() if title else None

        kv: dict[str, str] = {}
        for li in tree.css("ul#top-ratios li"):
            name = li.css_first("span.name")
            value = li.css_first("span.value")
            if name and value:
                kv[name.text(strip=True)] = value.text(strip=True)

        return {"company_name": company_name, "top_ratios": kv}

    def _table_from_section(self, tree: HTMLParser, section_id: str) -> dict[str, Any]:
        section = tree.css_first(f"section#{section_id}")
        if not section:
            return {"columns": [], "rows": []}

        table = section.css_first("table")
        if not table:
            return {"columns": [], "rows": []}

        columns = [th.text(strip=True) for th in table.css("thead th")]
        rows = []
        for tr in table.css("tbody tr"):
            cells = [td.text(separator=" ", strip=True) for td in tr.css("td")]
            if cells:
                rows.append(cells)

        return {"columns": columns, "rows": rows}

    def _extract_documents(self, tree: HTMLParser) -> dict[str, Any]:
        section = tree.css_first("section#documents")
        if not section:
            return {"links": []}

        links = []
        seen = set()
        for a in section.css("a[href]"):
            href = (a.attributes.get("href") or "").strip()
            text = a.text(strip=True)
            if not href:
                continue
            key = (href, text)
            if key in seen:
                continue
            seen.add(key)
            links.append({"text": text, "href": href})

        return {"links": links}

    def _extract_insights(self, tree: HTMLParser) -> dict[str, Any]:
        section = tree.css_first("section#insights")
        if not section:
            return {"items": []}

        items = []
        for card in section.css(".insight-card, [data-insight], .insight"):
            txt = card.text(separator=" ", strip=True)
            if txt:
                items.append(txt)

        if not items:
            for p in section.css("p"):
                txt = p.text(separator=" ", strip=True)
                if txt:
                    items.append(txt)

        unique = []
        seen = set()
        for it in items:
            if it in seen:
                continue
            seen.add(it)
            unique.append(it)

        return {"items": unique}

    def fetch_company(self, symbol: str, mode: str = "consolidated", proxy_url: str | None = None) -> dict[str, Any]:
        url = self._url(symbol, mode)
        html = self._fetch_html(url, proxy_url=proxy_url)
        tree = HTMLParser(html)

        payload = {
            "symbol": symbol.upper(),
            "mode": mode,
            "overview": self._extract_overview(tree),
            "analysis": self._table_from_section(tree, "analysis"),
            "peers": self._table_from_section(tree, "peers"),
            "quarters": self._table_from_section(tree, "quarters"),
            "profit_loss": self._table_from_section(tree, "profit-loss"),
            "balance_sheet": self._table_from_section(tree, "balance-sheet"),
            "cash_flow": self._table_from_section(tree, "cash-flow"),
            "ratios": self._table_from_section(tree, "ratios"),
            "shareholding": self._table_from_section(tree, "shareholding"),
            "documents": self._extract_documents(tree),
            "insights": self._extract_insights(tree),
        }

        return {"data": payload, "meta": self._meta(url, proxy_url), "warnings": []}

    def fetch_company_raw(self, symbol: str, mode: str = "consolidated", proxy_url: str | None = None) -> dict[str, Any]:
        url = self._url(symbol, mode)
        html = self._fetch_html(url, proxy_url=proxy_url)
        tree = HTMLParser(html)
        sections = [s.attributes.get("id") for s in tree.css("section[id]") if s.attributes.get("id")]

        return {
            "data": {
                "symbol": symbol.upper(),
                "mode": mode,
                "sections": sections,
                "html": html,
            },
            "meta": self._meta(url, proxy_url),
            "warnings": [],
        }

    def fetch_company_tab(self, symbol: str, tab: str, mode: str = "consolidated", proxy_url: str | None = None) -> dict[str, Any]:
        url = self._url(symbol, mode)
        html = self._fetch_html(url, proxy_url=proxy_url)
        tree = HTMLParser(html)

        if tab == "documents":
            data = self._extract_documents(tree)
        elif tab == "insights":
            data = self._extract_insights(tree)
        else:
            section_id = TAB_TO_SECTION_ID.get(tab)
            data = self._table_from_section(tree, section_id) if section_id else {}

        return {
            "data": {
                "symbol": symbol.upper(),
                "mode": mode,
                "tab": tab,
                "result": data,
            },
            "meta": self._meta(url, proxy_url),
            "warnings": [],
        }

    def compare_companies(self, symbols: list[str], mode: str = "consolidated", proxy_url: str | None = None) -> dict[str, Any]:
        comparisons = []
        for symbol in symbols:
            company = self.fetch_company(symbol=symbol, mode=mode, proxy_url=proxy_url)["data"]
            overview = company.get("overview", {})
            top = overview.get("top_ratios", {})
            comparisons.append(
                {
                    "symbol": symbol.upper(),
                    "company_name": overview.get("company_name"),
                    "market_cap": top.get("Market Cap"),
                    "current_price": top.get("Current Price"),
                    "stock_pe": top.get("Stock P/E"),
                    "roe": top.get("ROE"),
                    "dividend_yield": top.get("Dividend Yield"),
                }
            )

        return {
            "data": {"mode": mode, "comparisons": comparisons},
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "parser_version": "0.5.0",
                "proxy_used": bool(proxy_url),
            },
            "warnings": [],
        }


    def _extract_locs(self, xml: str) -> list[str]:
        urls = []
        start = 0
        while True:
            i = xml.find("<loc>", start)
            if i == -1:
                break
            j = xml.find("</loc>", i)
            if j == -1:
                break
            url = xml[i + 5 : j].strip()
            urls.append(url)
            start = j + 6
        return urls

    def search_companies(self, query: str, limit: int = 10) -> dict[str, Any]:
        q = query.strip().lower()

        index_url = f"{BASE}/sitemap.xml"
        index_xml = self._fetch_html(index_url)
        sitemap_urls = self._extract_locs(index_xml)

        company_sitemaps = [u for u in sitemap_urls if "sitemap-companies.xml" in u]
        if not company_sitemaps:
            company_sitemaps = [f"{BASE}/sitemap-companies.xml"]

        results = []
        for sitemap_url in company_sitemaps:
            xml = self._fetch_html(sitemap_url)
            for url in self._extract_locs(xml):
                slug = url.rstrip("/").split("/")[-1]
                if slug.lower() == "consolidated":
                    slug = url.rstrip("/").split("/")[-2]
                if q in slug.lower():
                    results.append({"symbol": slug.upper(), "url": url})
                    if len(results) >= limit:
                        break
            if len(results) >= limit:
                break

        return {
            "data": {"query": query, "results": results},
            "meta": {
                "source_url": index_url,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "parser_version": "0.4.0",
                "searched_sitemaps": company_sitemaps,
            },
            "warnings": [],
        }
