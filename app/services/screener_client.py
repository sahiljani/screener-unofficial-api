from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import hashlib
import re
import time
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

from app.core.cache import CacheStore

BASE = "https://www.screener.in"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

TAB_TO_SECTION_ID = {
    "quarters": "quarters",
    "profit-loss": "profit-loss",
    "balance-sheet": "balance-sheet",
    "cash-flow": "cash-flow",
    "ratios": "ratios",
    "shareholding": "shareholding",
}

SECTOR_ALIAS_TO_SLUG = {
    "aerospace-defense": "Aerospace & Defense",
    "agricultural-food-other-products": "Agricultural Food & other Products",
    "agricultural-commercial-construction-vehicles": "Agricultural, Commercial & Construction Vehicles",
    "auto-components": "Auto Components",
    "automobiles": "Automobiles",
    "banks": "Banks",
    "beverages": "Beverages",
    "capital-markets": "Capital Markets",
    "cement-cement-products": "Cement & Cement Products",
    "chemicals-petrochemicals": "Chemicals & Petrochemicals",
    "cigarettes-tobacco-products": "Cigarettes & Tobacco Products",
    "commercial-services-supplies": "Commercial Services & Supplies",
    "construction": "Construction",
    "consumable-fuels": "Consumable Fuels",
    "consumer-durables": "Consumer Durables",
    "diversified": "Diversified",
    "diversified-fmcg": "Diversified FMCG",
    "diversified-metals": "Diversified Metals",
    "electrical-equipment": "Electrical Equipment",
    "engineering-services": "Engineering Services",
    "entertainment": "Entertainment",
    "ferrous-metals": "Ferrous Metals",
    "fertilizers-agrochemicals": "Fertilizers & Agrochemicals",
    "finance": "Finance",
    "financial-technology-fintech": "Financial Technology (Fintech)",
    "food-products": "Food Products",
    "gas": "Gas",
    "healthcare-equipment-supplies": "Healthcare Equipment & Supplies",
    "healthcare-services": "Healthcare Services",
    "household-products": "Household Products",
    "industrial-manufacturing": "Industrial Manufacturing",
    "industrial-products": "Industrial Products",
    "insurance": "Insurance",
    "it-hardware": "IT - Hardware",
    "it-services": "IT - Services",
    "it-software": "IT - Software",
    "leisure-services": "Leisure Services",
    "media": "Media",
    "metals-minerals-trading": "Metals & Minerals Trading",
    "minerals-mining": "Minerals & Mining",
    "non-ferrous-metals": "Non - Ferrous Metals",
    "oil": "Oil",
    "other-construction-materials": "Other Construction Materials",
    "other-consumer-services": "Other Consumer Services",
    "other-utilities": "Other Utilities",
    "paper-forest-jute-products": "Paper, Forest & Jute Products",
    "personal-products": "Personal Products",
    "petroleum-products": "Petroleum Products",
    "pharmaceuticals-biotechnology": "Pharmaceuticals & Biotechnology",
    "power": "Power",
    "printing-publication": "Printing & Publication",
    "realty": "Realty",
    "retailing": "Retailing",
    "telecom-equipment-accessories": "Telecom - Equipment & Accessories",
    "telecom-services": "Telecom - Services",
    "textiles-apparels": "Textiles & Apparels",
    "transport-infrastructure": "Transport Infrastructure",
    "transport-services": "Transport Services",
}


class ScreenerClient:
    def __init__(
        self,
        cache_ttl_seconds: int = 300,
        min_interval_seconds: float = 0.2,
        throttle_company_interval_seconds: float | None = None,
        throttle_sector_interval_seconds: float | None = None,
        throttle_screens_interval_seconds: float | None = None,
        upstream_max_retries: int = 2,
        upstream_retry_backoff_seconds: float = 0.5,
        cache_store: CacheStore | None = None,
        screens_max_pages_default: int = 20,
        max_crawl_seconds: float = 60.0,
    ):
        self.cache_ttl_seconds = cache_ttl_seconds
        self.min_interval_seconds = min_interval_seconds
        self.throttle_company_interval_seconds = (
            min_interval_seconds if throttle_company_interval_seconds is None else max(0.0, throttle_company_interval_seconds)
        )
        self.throttle_sector_interval_seconds = (
            min_interval_seconds if throttle_sector_interval_seconds is None else max(0.0, throttle_sector_interval_seconds)
        )
        self.throttle_screens_interval_seconds = (
            min_interval_seconds if throttle_screens_interval_seconds is None else max(0.0, throttle_screens_interval_seconds)
        )

        self.upstream_max_retries = max(0, upstream_max_retries)
        self.upstream_retry_backoff_seconds = max(0.0, upstream_retry_backoff_seconds)

        self.screens_max_pages_default = max(1, screens_max_pages_default)
        self.max_crawl_seconds = max(5.0, max_crawl_seconds)

        self.cache_store = cache_store or CacheStore(backend='memory')

        self._last_request_at_by_scope = {
            'company': 0.0,
            'sector': 0.0,
            'screens': 0.0,
            'default': 0.0,
        }

    def _url(self, symbol: str, mode: str) -> str:
        s = symbol.strip().upper()
        if mode == "consolidated":
            return f"{BASE}/company/{s}/consolidated/"
        return f"{BASE}/company/{s}/"

    def _cache_key(self, url: str, proxy_url: str | None = None) -> str:
        raw = f"{proxy_url or 'direct'}::{url}"
        digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        return f"html:{digest}"

    def _scope_for_url(self, url: str) -> str:
        u = url.lower()
        if '/screens/' in u:
            return 'screens'
        if '/market/' in u:
            return 'sector'
        if '/company/' in u:
            return 'company'
        return 'default'

    def _throttle_for_scope(self, scope: str) -> None:
        if scope == 'company':
            interval = self.throttle_company_interval_seconds
        elif scope == 'sector':
            interval = self.throttle_sector_interval_seconds
        elif scope == 'screens':
            interval = self.throttle_screens_interval_seconds
        else:
            interval = self.min_interval_seconds

        now = time.time()
        last = self._last_request_at_by_scope.get(scope, 0.0)
        wait_for = interval - (now - last)
        if wait_for > 0:
            time.sleep(wait_for)
        self._last_request_at_by_scope[scope] = time.time()

    def _http_get_once(self, url: str, proxy_url: str | None = None) -> str:
        with httpx.Client(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": UA},
            proxy=proxy_url if proxy_url else None,
        ) as c:
            r = c.get(url)
            r.raise_for_status()
            return r.text

    def _fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        scope = self._scope_for_url(url)

        attempt = 0
        while True:
            self._throttle_for_scope(scope)
            try:
                return self._http_get_once(url, proxy_url=proxy_url)
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code if exc.response is not None else None
                retryable = code in {429, 500, 502, 503, 504}
                if retryable and attempt < self.upstream_max_retries:
                    attempt += 1
                    time.sleep(self.upstream_retry_backoff_seconds * (2 ** (attempt - 1)))
                    continue
                raise
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.NetworkError):
                if attempt < self.upstream_max_retries:
                    attempt += 1
                    time.sleep(self.upstream_retry_backoff_seconds * (2 ** (attempt - 1)))
                    continue
                raise

    def _fetch_html(self, url: str, proxy_url: str | None = None) -> str:
        key = self._cache_key(url, proxy_url)
        hit = self.cache_store.get(key)
        if hit is not None:
            return hit

        html = self._fetch_html_raw(url, proxy_url=proxy_url)
        self.cache_store.set(key, html, ttl_seconds=self.cache_ttl_seconds)
        return html

    # ── Async HTTP methods ──────────────────────────────────────────

    async def _async_http_get_once(self, url: str, proxy_url: str | None = None) -> str:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": UA},
            proxy=proxy_url if proxy_url else None,
        ) as c:
            r = await c.get(url)
            r.raise_for_status()
            return r.text

    async def _async_throttle_for_scope(self, scope: str) -> None:
        if scope == 'company':
            interval = self.throttle_company_interval_seconds
        elif scope == 'sector':
            interval = self.throttle_sector_interval_seconds
        elif scope == 'screens':
            interval = self.throttle_screens_interval_seconds
        else:
            interval = self.min_interval_seconds

        now = time.time()
        last = self._last_request_at_by_scope.get(scope, 0.0)
        wait_for = interval - (now - last)
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        self._last_request_at_by_scope[scope] = time.time()

    async def _async_fetch_html_raw(self, url: str, proxy_url: str | None = None) -> str:
        scope = self._scope_for_url(url)
        attempt = 0
        while True:
            await self._async_throttle_for_scope(scope)
            try:
                return await self._async_http_get_once(url, proxy_url=proxy_url)
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code if exc.response is not None else None
                retryable = code in {429, 500, 502, 503, 504}
                if retryable and attempt < self.upstream_max_retries:
                    attempt += 1
                    await asyncio.sleep(self.upstream_retry_backoff_seconds * (2 ** (attempt - 1)))
                    continue
                raise
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.NetworkError):
                if attempt < self.upstream_max_retries:
                    attempt += 1
                    await asyncio.sleep(self.upstream_retry_backoff_seconds * (2 ** (attempt - 1)))
                    continue
                raise

    async def _async_fetch_html(self, url: str, proxy_url: str | None = None) -> str:
        key = self._cache_key(url, proxy_url)
        hit = self.cache_store.get(key)
        if hit is not None:
            return hit

        html = await self._async_fetch_html_raw(url, proxy_url=proxy_url)
        self.cache_store.set(key, html, ttl_seconds=self.cache_ttl_seconds)
        return html

    def _meta(self, url: str, proxy_url: str | None, parser_version: str = "0.6.0") -> dict[str, Any]:
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

    def _extract_table(self, table_node) -> dict[str, Any]:
        if not table_node:
            return {"columns": [], "rows": []}

        thead_columns = [th.text(strip=True) for th in table_node.css("thead th")]
        if thead_columns:
            columns = thead_columns
            row_nodes = table_node.css("tbody tr")
        else:
            all_rows = table_node.css("tr")
            if not all_rows:
                return {"columns": [], "rows": []}
            header_cells = all_rows[0].css("th, td")
            columns = [c.text(separator=" ", strip=True) for c in header_cells]
            row_nodes = all_rows[1:]

        rows = []
        for tr in row_nodes:
            cells = [td.text(separator=" ", strip=True) for td in tr.css("th, td")]
            if cells:
                rows.append(cells)

        return {"columns": columns, "rows": rows}

    def _table_from_section(self, tree: HTMLParser, section_id: str) -> dict[str, Any]:
        section = tree.css_first(f"section#{section_id}")
        if not section:
            return {"columns": [], "rows": []}

        table = section.css_first("table")
        return self._extract_table(table)

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

    def _extract_analysis(self, tree: HTMLParser) -> dict[str, Any]:
        section = tree.css_first("section#analysis")
        if not section:
            return {"pros": [], "cons": [], "notes": []}

        pros = [li.text(separator=" ", strip=True) for li in section.css(".pros li") if li.text(strip=True)]
        cons = [li.text(separator=" ", strip=True) for li in section.css(".cons li") if li.text(strip=True)]

        notes: list[str] = []
        for p in section.css("p"):
            txt = p.text(separator=" ", strip=True)
            if txt:
                notes.append(txt)

        if not pros and not cons:
            for li in section.css("li"):
                txt = li.text(separator=" ", strip=True)
                if txt:
                    notes.append(txt)

        unique_notes = []
        seen = set()
        for n in notes:
            if n in seen:
                continue
            seen.add(n)
            unique_notes.append(n)

        return {
            "pros": pros,
            "cons": cons,
            "notes": unique_notes,
        }

    def _company_info_ids(self, tree: HTMLParser) -> dict[str, str | None]:
        info = tree.css_first("#company-info")
        if not info:
            return {"company_id": None, "warehouse_id": None}
        return {
            "company_id": info.attributes.get("data-company-id"),
            "warehouse_id": info.attributes.get("data-warehouse-id"),
        }

    def _extract_peers(self, tree: HTMLParser, proxy_url: str | None = None) -> dict[str, Any]:
        ids = self._company_info_ids(tree)
        warehouse_id = ids.get("warehouse_id")

        # Primary source: Screener peers API endpoint rendered server-side as HTML table.
        if warehouse_id:
            peers_url = f"{BASE}/api/company/{warehouse_id}/peers/"
            try:
                peers_html = self._fetch_html(peers_url, proxy_url=proxy_url)
                peers_tree = HTMLParser(peers_html)
                table = peers_tree.css_first("table")
                parsed = self._extract_table(table)
                if parsed["columns"] or parsed["rows"]:
                    return {
                        "columns": parsed["columns"],
                        "rows": parsed["rows"],
                        "warehouse_id": warehouse_id,
                    }
            except Exception:
                pass

        # Fallback for tests / static fixtures.
        parsed = self._table_from_section(tree, "peers")
        return {
            "columns": parsed["columns"],
            "rows": parsed["rows"],
            "warehouse_id": warehouse_id,
        }

    def fetch_company(self, symbol: str, mode: str = "consolidated", proxy_url: str | None = None) -> dict[str, Any]:
        url = self._url(symbol, mode)
        html = self._fetch_html(url, proxy_url=proxy_url)
        tree = HTMLParser(html)

        payload = {
            "symbol": symbol.upper(),
            "mode": mode,
            "overview": self._extract_overview(tree),
            "analysis": self._extract_analysis(tree),
            "peers": self._extract_peers(tree, proxy_url=proxy_url),
            "quarters": self._table_from_section(tree, "quarters"),
            "profit_loss": self._table_from_section(tree, "profit-loss"),
            "balance_sheet": self._table_from_section(tree, "balance-sheet"),
            "cash_flow": self._table_from_section(tree, "cash-flow"),
            "ratios": self._table_from_section(tree, "ratios"),
            "shareholding": self._table_from_section(tree, "shareholding"),
            "documents": self._extract_documents(tree),
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
        elif tab == "analysis":
            data = self._extract_analysis(tree)
        elif tab == "peers":
            data = self._extract_peers(tree, proxy_url=proxy_url)
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
                "parser_version": "0.6.0",
                "proxy_used": bool(proxy_url),
            },
            "warnings": [],
        }

    def _slugify(self, value: str) -> str:
        value = value.lower().strip()
        value = value.replace("&", " and ")
        value = value.replace("/", " ")
        value = value.replace("(", " ").replace(")", " ")
        value = value.replace(",", " ")
        value = value.replace("-", " ")
        value = re.sub(r"\s+", " ", value)
        value = value.replace(" and ", "-")
        value = value.replace(" ", "-")
        value = re.sub(r"-+", "-", value).strip("-")
        return value

    def _market_table_node(self, tree: HTMLParser):
        return tree.css_first("[data-page-results] table") or tree.css_first("table.data-table")

    def _extract_market_rows(self, tree: HTMLParser) -> tuple[list[str], list[list[str]]]:
        table = self._market_table_node(tree)
        if not table:
            return [], []

        rows = table.css("tr")
        if not rows:
            return [], []

        columns = [c.text(separator=" ", strip=True) for c in rows[0].css("th,td")]
        data_rows: list[list[str]] = []
        for tr in rows[1:]:
            row = [c.text(separator=" ", strip=True) for c in tr.css("th,td")]
            if row:
                data_rows.append(row)

        return columns, data_rows

    def _extract_columns_meta(self, tree: HTMLParser) -> list[dict[str, str | None]]:
        table = self._market_table_node(tree)
        if not table:
            return []

        header_row = table.css_first("tr")
        if not header_row:
            return []

        meta: list[dict[str, str | None]] = []
        for idx, cell in enumerate(header_row.css("th,td")):
            label = cell.text(separator=" ", strip=True)
            tooltip = (cell.attributes.get("data-tooltip") or "").strip() or None
            title = (cell.attributes.get("title") or "").strip() or None
            unit = None
            unit_node = cell.css_first("span")
            if unit_node:
                unit = unit_node.text(separator=" ", strip=True) or None

            meta.append(
                {
                    "index": idx,
                    "name": label,
                    "tooltip": tooltip,
                    "title": title,
                    "unit": unit,
                }
            )

        return meta

    def _extract_pagination(self, tree: HTMLParser) -> tuple[int | None, int | None]:
        current_page: int | None = None
        total_pages: int | None = None

        for a in tree.css(".pagination a[href]"):
            text = a.text(strip=True)
            href = a.attributes.get("href") or ""
            if text.isdigit() and href.startswith("#"):
                try:
                    current_page = int(text)
                except ValueError:
                    pass

            parsed = parse_qs(urlparse(href).query)
            for value in parsed.get("page", []):
                try:
                    total_pages = max(total_pages or 0, int(value))
                except ValueError:
                    continue

        return current_page, total_pages

    def _extract_market_result_count(self, tree: HTMLParser) -> int | None:
        root_text = tree.body.text(separator=" ", strip=True) if tree.body else tree.text(separator=" ", strip=True)
        m = re.search(r"(\d+)\s+results\s+found", root_text, flags=re.IGNORECASE)
        if not m:
            return None
        try:
            return int(m.group(1))
        except ValueError:
            return None

    def _extract_market_hierarchy(self, tree: HTMLParser) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        seen = set()
        for p in tree.css("p.sub"):
            for a in p.css("a[href]"):
                name = a.text(separator=" ", strip=True)
                href = a.attributes.get("href") or ""
                if not name or not href.startswith("/market/"):
                    continue
                key = (name, href)
                if key in seen:
                    continue
                seen.add(key)
                out.append({"name": name, "url": urljoin(BASE, href)})
            if out:
                break
        return out

    def _extract_sector_links(self, html: str) -> dict[str, str]:
        tree = HTMLParser(html)
        links: dict[str, str] = {}
        for a in tree.css("a[href]"):
            href = (a.attributes.get("href") or "").strip()
            name = a.text(separator=" ", strip=True)
            if not name or not href.startswith("/market/"):
                continue
            if href.count("/") < 5:
                continue
            if name in links:
                continue
            links[name] = urljoin(BASE, href)
        return links

    def _market_common_parent_url(self, urls: list[str]) -> str | None:
        if not urls:
            return None

        split_paths = []
        for u in urls:
            segments = [seg for seg in urlparse(u).path.split("/") if seg]
            if len(segments) < 4 or segments[0] != "market":
                continue
            split_paths.append(segments)

        if not split_paths:
            return None

        common: list[str] = []
        for group in zip(*split_paths):
            if len(set(group)) == 1:
                common.append(group[0])
            else:
                break

        if len(common) < 4:
            return None

        return f"{BASE}/{'/'.join(common)}/"

    def _resolve_sector_url(self, canonical_name: str, links: dict[str, str]) -> str | None:
        # 1) exact name match
        if canonical_name in links:
            return links[canonical_name]

        # 2) slug-equivalent match
        wanted_slug = self._slugify(canonical_name)
        for name, link in links.items():
            if self._slugify(name) == wanted_slug:
                return link

        # 3) compound-name fallback (e.g. "Pharmaceuticals & Biotechnology")
        parts = [p.strip() for p in re.split(r"[&,/]", canonical_name) if p.strip()]
        if len(parts) >= 2:
            part_urls: list[str] = []
            for part in parts:
                part_slug = self._slugify(part)
                for name, link in links.items():
                    name_slug = self._slugify(name)
                    if part_slug and (part_slug in name_slug or name_slug in part_slug):
                        part_urls.append(link)
                        break

            parent = self._market_common_parent_url(part_urls)
            if parent:
                return parent

        # 4) best-effort token-overlap fallback
        wanted_tokens = {t for t in self._slugify(canonical_name).split("-") if t and t not in {"other", "and"}}
        best_score = 0
        best_link = None
        for name, link in links.items():
            tokens = {t for t in self._slugify(name).split("-") if t and t not in {"other", "and"}}
            score = len(wanted_tokens & tokens)
            if score > best_score:
                best_score = score
                best_link = link

        return best_link if best_score >= 2 else None

    def list_sectors(self, proxy_url: str | None = None) -> dict[str, Any]:
        url = f"{BASE}/market/"
        html = self._fetch_html(url, proxy_url=proxy_url)
        links = self._extract_sector_links(html)

        sectors = []
        for alias, canonical_name in SECTOR_ALIAS_TO_SLUG.items():
            sector_url = self._resolve_sector_url(canonical_name, links)
            sectors.append(
                {
                    "name": canonical_name,
                    "slug": alias,
                    "url": sector_url,
                    "available": bool(sector_url),
                }
            )

        return {
            "data": {
                "sectors": sectors,
                "count": len(sectors),
            },
            "meta": self._meta(url, proxy_url, parser_version="0.7.0"),
            "warnings": [],
        }

    def fetch_sector_data(
        self,
        sector: str,
        page: int = 1,
        limit: int = 50,
        include_all_pages: bool = False,
        proxy_url: str | None = None,
    ) -> dict[str, Any]:
        links = self._extract_sector_links(self._fetch_html(f"{BASE}/market/", proxy_url=proxy_url))

        canonical_name = SECTOR_ALIAS_TO_SLUG.get(sector)
        if not canonical_name:
            # allow direct sector names too
            canonical_name = next((name for name in SECTOR_ALIAS_TO_SLUG.values() if self._slugify(name) == self._slugify(sector)), None)
        if not canonical_name:
            raise ValueError(f"Unknown sector '{sector}'")

        sector_url = self._resolve_sector_url(canonical_name, links)
        if not sector_url:
            raise ValueError(f"Sector '{canonical_name}' URL not found on Screener market page")

        parsed = urlparse(sector_url)
        base_sector_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        def _fetch_page(p: int) -> dict[str, Any]:
            page_url = f"{base_sector_url}?limit={limit}&page={p}"
            html = self._fetch_html(page_url, proxy_url=proxy_url)
            tree = HTMLParser(html)

            title = tree.css_first("h1")
            sector_title = title.text(separator=" ", strip=True) if title else canonical_name

            columns, rows = self._extract_market_rows(tree)
            current_page, total_pages = self._extract_pagination(tree)
            total_results = self._extract_market_result_count(tree)
            hierarchy = self._extract_market_hierarchy(tree)

            return {
                "page": p,
                "url": page_url,
                "sector_title": sector_title,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "pagination": {
                    "current_page": current_page or p,
                    "total_pages": total_pages,
                    "limit": limit,
                },
                "total_results": total_results,
                "hierarchy": hierarchy,
            }

        first = _fetch_page(page)

        if not include_all_pages:
            return {
                "data": {
                    "sector": canonical_name,
                    "slug": self._slugify(canonical_name),
                    "base_url": base_sector_url,
                    "page": first,
                },
                "meta": self._meta(first["url"], proxy_url, parser_version="0.7.0"),
                "warnings": [],
            }

        total_pages = first["pagination"].get("total_pages") or 1
        pages = [first]
        for p in range(page + 1, total_pages + 1):
            pages.append(_fetch_page(p))

        return {
            "data": {
                "sector": canonical_name,
                "slug": self._slugify(canonical_name),
                "base_url": base_sector_url,
                "pages": pages,
                "summary": {
                    "from_page": page,
                    "to_page": total_pages,
                    "pages_fetched": len(pages),
                    "rows_fetched": sum(pg["row_count"] for pg in pages),
                },
            },
            "meta": self._meta(first["url"], proxy_url, parser_version="0.7.0"),
            "warnings": [],
        }

    def _extract_screens_from_page(self, tree: HTMLParser) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen = set()

        for li in tree.css("ul.items li"):
            a = li.css_first("a[href]")
            if not a:
                continue

            href = (a.attributes.get("href") or "").strip()
            if not href.startswith("/screens/"):
                continue

            m = re.match(r"^/screens/(\d+)/([^/]+)/?$", href)
            if not m:
                continue

            screen_id = int(m.group(1))
            slug = m.group(2)
            title_node = a.css_first("strong")
            desc_node = a.css_first("span.sub")

            title = title_node.text(separator=" ", strip=True) if title_node else a.text(separator=" ", strip=True)
            description = desc_node.text(separator=" ", strip=True) if desc_node else None

            key = (screen_id, slug)
            if key in seen:
                continue
            seen.add(key)

            items.append(
                {
                    "screen_id": screen_id,
                    "slug": slug,
                    "title": title,
                    "description": description,
                    "url": urljoin(BASE, href),
                }
            )

        return items

    def _extract_screens_pagination(self, tree: HTMLParser) -> tuple[int, int]:
        current_page = 1
        total_pages: int | None = None

        for a in tree.css(".pagination a[href]"):
            text = a.text(strip=True)
            href = a.attributes.get("href") or ""

            if text.isdigit() and href.startswith("#"):
                try:
                    current_page = int(text)
                except ValueError:
                    pass

            parsed = parse_qs(urlparse(href).query)
            for value in parsed.get("page", []):
                try:
                    total_pages = max(total_pages or 0, int(value))
                except ValueError:
                    continue

        # Sparse / edge pagination fallback:
        # if we cannot infer total_pages from links, assume current page is the last known page.
        if total_pages is None:
            total_pages = current_page

        # If current page is marked active (#) and exceeds link max (e.g. page=50), prefer current page.
        total_pages = max(total_pages, current_page)

        return current_page, total_pages

    @staticmethod
    def _apply_filters(items: list[dict[str, Any]], filters: str | None) -> tuple[list[dict[str, Any]], bool]:
        """Apply recognized filter expressions to items. Returns (filtered_items, any_applied)."""
        if not filters:
            return items, False

        any_applied = False
        for token in filters.split(","):
            token = token.strip()
            if token == "has:description":
                items = [i for i in items if i.get("description")]
                any_applied = True
            elif token.startswith("id_gt:"):
                try:
                    threshold = int(token.split(":", 1)[1])
                    items = [i for i in items if i.get("screen_id", 0) > threshold]
                    any_applied = True
                except ValueError:
                    pass
            elif token.startswith("id_lt:"):
                try:
                    threshold = int(token.split(":", 1)[1])
                    items = [i for i in items if i.get("screen_id", 0) < threshold]
                    any_applied = True
                except ValueError:
                    pass
        return items, any_applied

    @staticmethod
    def _apply_search(items: list[dict[str, Any]], q: str | None) -> list[dict[str, Any]]:
        """Filter items where q appears in title or description (case-insensitive)."""
        if not q:
            return items
        q_lower = q.lower()
        return [
            i for i in items
            if q_lower in (i.get("title") or "").lower()
            or q_lower in (i.get("description") or "").lower()
        ]

    @staticmethod
    def _apply_sort(items: list[dict[str, Any]], sort: str | None, order: str | None) -> list[dict[str, Any]]:
        """Sort items by field. Default order: asc for title, desc for screen_id."""
        if not sort or sort not in ("title", "screen_id"):
            return items
        default_order = "asc" if sort == "title" else "desc"
        effective_order = order if order in ("asc", "desc") else default_order
        reverse = effective_order == "desc"
        if sort == "title":
            return sorted(items, key=lambda i: (i.get("title") or "").lower(), reverse=reverse)
        return sorted(items, key=lambda i: i.get("screen_id", 0), reverse=reverse)

    def list_screens(
        self,
        page: int = 1,
        include_all_pages: bool = False,
        max_pages: int | None = None,
        proxy_url: str | None = None,
        filters: str | None = None,
        q: str | None = None,
        sort: str | None = None,
        order: str | None = None,
    ) -> dict[str, Any]:
        if max_pages is not None and max_pages < 1:
            raise ValueError("max_pages must be >= 1")

        filters_payload: dict[str, Any] = {
            "raw": filters,
            "applied": False,
            "note": "Filters placeholder is accepted for forward compatibility and currently not applied upstream.",
        }

        def _fetch_page(p: int) -> dict[str, Any]:
            page_url = f"{BASE}/screens/?page={p}"
            html = self._fetch_html(page_url, proxy_url=proxy_url)
            tree = HTMLParser(html)

            title = tree.css_first("h1")
            heading = title.text(separator=" ", strip=True) if title else "Popular Stock Screens"
            items = self._extract_screens_from_page(tree)
            current_page, total_pages = self._extract_screens_pagination(tree)

            return {
                "page": p,
                "url": page_url,
                "heading": heading,
                "items": items,
                "item_count": len(items),
                "pagination": {
                    "current_page": current_page or p,
                    "total_pages": total_pages,
                },
            }

        first = _fetch_page(page)

        def _post_process_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            """Apply filters, search, and sort to a list of screen items."""
            nonlocal filters_payload
            filtered, any_applied = self._apply_filters(items, filters)
            if any_applied:
                filters_payload = {**filters_payload, "applied": True, "note": "One or more filters were applied client-side."}
            filtered = self._apply_search(filtered, q)
            filtered = self._apply_sort(filtered, sort, order)
            return filtered

        search_info: dict[str, Any] | None = None

        if not include_all_pages:
            first["items"] = _post_process_items(first["items"])
            first["item_count"] = len(first["items"])
            if q:
                search_info = {"query": q, "matched": first["item_count"]}
            result: dict[str, Any] = {
                "data": {
                    "page": first,
                    "filters": filters_payload,
                },
                "meta": self._meta(first["url"], proxy_url, parser_version="1.1.0"),
                "warnings": [],
            }
            if search_info:
                result["data"]["search"] = search_info
            return result

        warnings: list[str] = []

        total_pages = first["pagination"].get("total_pages") or page
        effective_max = max_pages if max_pages is not None else self.screens_max_pages_default
        if max_pages is None:
            warnings.append(f"max_pages defaulted to {self.screens_max_pages_default}; pass max_pages explicitly to override")
        target_last_page = min(total_pages, page + effective_max - 1)

        pages = [first]
        seen_screen_ids = {item["screen_id"] for item in first["items"]}
        duplicates_skipped = 0
        crawl_start = time.monotonic()
        timed_out = False

        for p in range(page + 1, target_last_page + 1):
            if time.monotonic() - crawl_start > self.max_crawl_seconds:
                warnings.append(f"Crawl stopped after {len(pages)} pages due to {self.max_crawl_seconds}s timeout")
                timed_out = True
                break
            pg = _fetch_page(p)
            deduped_items = []
            for item in pg["items"]:
                sid = item.get("screen_id")
                if sid in seen_screen_ids:
                    duplicates_skipped += 1
                    continue
                seen_screen_ids.add(sid)
                deduped_items.append(item)
            pg["items"] = deduped_items
            pg["item_count"] = len(deduped_items)
            pages.append(pg)

        # Apply search/sort/filters across all pages
        for pg in pages:
            pg["items"] = _post_process_items(pg["items"])
            pg["item_count"] = len(pg["items"])

        total_matched = sum(pg["item_count"] for pg in pages)
        if q:
            search_info = {"query": q, "matched": total_matched}

        result = {
            "data": {
                "pages": pages,
                "summary": {
                    "from_page": page,
                    "to_page": pages[-1]["page"],
                    "pages_fetched": len(pages),
                    "screens_fetched": total_matched,
                    "duplicates_skipped": duplicates_skipped,
                    "max_pages_applied": max_pages is not None or timed_out,
                },
                "filters": filters_payload,
            },
            "meta": self._meta(first["url"], proxy_url, parser_version="1.1.0"),
            "warnings": warnings,
        }
        if search_info:
            result["data"]["search"] = search_info
        return result

    def screens_pages(self, page: int = 1, proxy_url: str | None = None) -> dict[str, Any]:
        page_url = f"{BASE}/screens/?page={page}"
        html = self._fetch_html(page_url, proxy_url=proxy_url)
        tree = HTMLParser(html)

        current_page, total_pages = self._extract_screens_pagination(tree)
        items = self._extract_screens_from_page(tree)

        return {
            "data": {
                "page": {
                    "page": page,
                    "url": page_url,
                    "current_page": current_page,
                    "total_pages": total_pages,
                    "screens_on_page": len(items),
                }
            },
            "meta": self._meta(page_url, proxy_url, parser_version="0.9.0"),
            "warnings": [],
        }

    # ── Async screens methods ─────────────────────────────────────

    async def async_screens_pages(self, page: int = 1, proxy_url: str | None = None) -> dict[str, Any]:
        page_url = f"{BASE}/screens/?page={page}"
        html = await self._async_fetch_html(page_url, proxy_url=proxy_url)
        tree = HTMLParser(html)

        current_page, total_pages = self._extract_screens_pagination(tree)
        items = self._extract_screens_from_page(tree)

        return {
            "data": {
                "page": {
                    "page": page,
                    "url": page_url,
                    "current_page": current_page,
                    "total_pages": total_pages,
                    "screens_on_page": len(items),
                }
            },
            "meta": self._meta(page_url, proxy_url, parser_version="0.9.0"),
            "warnings": [],
        }

    async def async_list_screens(
        self,
        page: int = 1,
        include_all_pages: bool = False,
        max_pages: int | None = None,
        proxy_url: str | None = None,
        filters: str | None = None,
        q: str | None = None,
        sort: str | None = None,
        order: str | None = None,
    ) -> dict[str, Any]:
        if max_pages is not None and max_pages < 1:
            raise ValueError("max_pages must be >= 1")

        filters_payload: dict[str, Any] = {
            "raw": filters,
            "applied": False,
            "note": "Filters placeholder is accepted for forward compatibility and currently not applied upstream.",
        }

        async def _fetch_page(p: int) -> dict[str, Any]:
            page_url = f"{BASE}/screens/?page={p}"
            html = await self._async_fetch_html(page_url, proxy_url=proxy_url)
            tree = HTMLParser(html)

            title = tree.css_first("h1")
            heading = title.text(separator=" ", strip=True) if title else "Popular Stock Screens"
            items = self._extract_screens_from_page(tree)
            current_page, total_pages = self._extract_screens_pagination(tree)

            return {
                "page": p,
                "url": page_url,
                "heading": heading,
                "items": items,
                "item_count": len(items),
                "pagination": {
                    "current_page": current_page or p,
                    "total_pages": total_pages,
                },
            }

        first = await _fetch_page(page)

        def _post_process_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            nonlocal filters_payload
            filtered, any_applied = self._apply_filters(items, filters)
            if any_applied:
                filters_payload = {**filters_payload, "applied": True, "note": "One or more filters were applied client-side."}
            filtered = self._apply_search(filtered, q)
            filtered = self._apply_sort(filtered, sort, order)
            return filtered

        search_info: dict[str, Any] | None = None

        if not include_all_pages:
            first["items"] = _post_process_items(first["items"])
            first["item_count"] = len(first["items"])
            if q:
                search_info = {"query": q, "matched": first["item_count"]}
            result: dict[str, Any] = {
                "data": {
                    "page": first,
                    "filters": filters_payload,
                },
                "meta": self._meta(first["url"], proxy_url, parser_version="1.1.0"),
                "warnings": [],
            }
            if search_info:
                result["data"]["search"] = search_info
            return result

        warnings: list[str] = []

        total_pages = first["pagination"].get("total_pages") or page
        effective_max = max_pages if max_pages is not None else self.screens_max_pages_default
        if max_pages is None:
            warnings.append(f"max_pages defaulted to {self.screens_max_pages_default}; pass max_pages explicitly to override")
        target_last_page = min(total_pages, page + effective_max - 1)

        # Fetch remaining pages concurrently with semaphore
        sem = asyncio.Semaphore(3)
        crawl_start = time.monotonic()

        async def _guarded_fetch(p: int) -> dict[str, Any] | None:
            if time.monotonic() - crawl_start > self.max_crawl_seconds:
                return None
            async with sem:
                return await _fetch_page(p)

        tasks = [_guarded_fetch(p) for p in range(page + 1, target_last_page + 1)]
        fetched = await asyncio.gather(*tasks)

        pages = [first]
        seen_screen_ids = {item["screen_id"] for item in first["items"]}
        duplicates_skipped = 0
        timed_out = False

        for pg in fetched:
            if pg is None:
                timed_out = True
                warnings.append(f"Crawl stopped after {len(pages)} pages due to {self.max_crawl_seconds}s timeout")
                break
            deduped_items = []
            for item in pg["items"]:
                sid = item.get("screen_id")
                if sid in seen_screen_ids:
                    duplicates_skipped += 1
                    continue
                seen_screen_ids.add(sid)
                deduped_items.append(item)
            pg["items"] = deduped_items
            pg["item_count"] = len(deduped_items)
            pages.append(pg)

        for pg in pages:
            pg["items"] = _post_process_items(pg["items"])
            pg["item_count"] = len(pg["items"])

        total_matched = sum(pg["item_count"] for pg in pages)
        if q:
            search_info = {"query": q, "matched": total_matched}

        result = {
            "data": {
                "pages": pages,
                "summary": {
                    "from_page": page,
                    "to_page": pages[-1]["page"],
                    "pages_fetched": len(pages),
                    "screens_fetched": total_matched,
                    "duplicates_skipped": duplicates_skipped,
                    "max_pages_applied": max_pages is not None or timed_out,
                },
                "filters": filters_payload,
            },
            "meta": self._meta(first["url"], proxy_url, parser_version="1.1.0"),
            "warnings": warnings,
        }
        if search_info:
            result["data"]["search"] = search_info
        return result

    async def async_fetch_screen_details(
        self,
        screen_id: int,
        slug: str,
        page: int = 1,
        limit: int = 50,
        include_all_pages: bool = False,
        proxy_url: str | None = None,
    ) -> dict[str, Any]:
        def _is_valid_screen_page(payload: dict[str, Any]) -> bool:
            title = (payload.get("title") or "").strip().lower()
            if not title:
                return False
            if title in {"register", "login", "page not found", "not found"}:
                return False
            has_query = bool((payload.get("query") or "").strip())
            has_rows = bool(payload.get("row_count", 0) > 0)
            return has_query or has_rows

        async def _run_for_slug(active_slug: str) -> tuple[str, str, dict[str, Any], list[dict[str, Any]] | None, list[str]]:
            base_url = f"{BASE}/screens/{screen_id}/{active_slug}/"

            async def _fetch_page(p: int) -> dict[str, Any]:
                page_url = f"{base_url}?limit={limit}&page={p}"
                html = await self._async_fetch_html(page_url, proxy_url=proxy_url)
                tree = HTMLParser(html)

                heading = tree.css_first("h1")
                title = heading.text(separator=" ", strip=True) if heading else None

                query_node = tree.css_first("#query-builder")
                query = query_node.text(separator="\n", strip=True) if query_node else None

                author = None
                owner_profile_url = None
                for pnode in tree.css("p.sub"):
                    txt = pnode.text(separator=" ", strip=True)
                    if txt.lower().startswith("by "):
                        author = txt[3:].strip()
                        a = pnode.css_first("a[href]")
                        if a:
                            href = (a.attributes.get("href") or "").strip()
                            if href:
                                owner_profile_url = urljoin(BASE, href)
                        break

                export_url = None
                export_form = tree.css_first("form[action*='/api/export/screen/']")
                if export_form:
                    action = (export_form.attributes.get("action") or "").strip()
                    if action:
                        export_url = urljoin(BASE, action)

                source_id = None
                sort_val = None
                order_val = None
                for inp in tree.css("input[type='hidden']"):
                    name = (inp.attributes.get("name") or "").strip()
                    value = (inp.attributes.get("value") or "").strip()
                    if name == "source_id":
                        source_id = value or None
                    elif name == "sort":
                        sort_val = value or None
                    elif name == "order":
                        order_val = value or None

                columns, rows = self._extract_market_rows(tree)
                columns_meta = self._extract_columns_meta(tree)
                current_page, total_pages = self._extract_pagination(tree)
                total_results = self._extract_market_result_count(tree)

                return {
                    "page": p,
                    "url": page_url,
                    "title": title,
                    "author": author,
                    "owner_profile_url": owner_profile_url,
                    "query": query,
                    "export_url": export_url,
                    "source_id": source_id,
                    "sort": sort_val,
                    "order": order_val,
                    "columns": columns,
                    "columns_meta": columns_meta,
                    "rows": rows,
                    "row_count": len(rows),
                    "pagination": {
                        "current_page": current_page or p,
                        "total_pages": total_pages,
                        "limit": limit,
                    },
                    "total_results": total_results,
                }

            first = await _fetch_page(page)
            if not include_all_pages:
                return active_slug, base_url, first, None, []

            total_pages = first["pagination"].get("total_pages") or 1
            effective_max = min(total_pages, page + self.screens_max_pages_default - 1)

            sem = asyncio.Semaphore(3)
            crawl_start = time.monotonic()
            detail_warnings: list[str] = []

            async def _guarded_fetch(p: int) -> dict[str, Any] | None:
                if time.monotonic() - crawl_start > self.max_crawl_seconds:
                    return None
                async with sem:
                    return await _fetch_page(p)

            tasks = [_guarded_fetch(p) for p in range(page + 1, effective_max + 1)]
            fetched = await asyncio.gather(*tasks)

            all_pages = [first]
            for pg in fetched:
                if pg is None:
                    detail_warnings.append(f"Crawl stopped after {len(all_pages)} pages due to {self.max_crawl_seconds}s timeout")
                    break
                all_pages.append(pg)

            return active_slug, base_url, first, all_pages, detail_warnings

        active_slug, base_url, first, pages, crawl_warnings = await _run_for_slug(slug)

        if not _is_valid_screen_page(first):
            resolved = self._resolve_screen_slug(screen_id=screen_id, proxy_url=proxy_url)
            if resolved and resolved != active_slug:
                active_slug, base_url, first, pages, crawl_warnings = await _run_for_slug(resolved)

        if not first.get("title"):
            raise ValueError("Screen not found or inaccessible")

        if not include_all_pages:
            return {
                "data": {
                    "screen_id": screen_id,
                    "slug": active_slug,
                    "base_url": base_url,
                    "page": first,
                },
                "meta": self._meta(first["url"], proxy_url, parser_version="1.2.0"),
                "warnings": crawl_warnings,
            }

        pages = pages or [first]
        return {
            "data": {
                "screen_id": screen_id,
                "slug": active_slug,
                "base_url": base_url,
                "pages": pages,
                "summary": {
                    "from_page": page,
                    "to_page": pages[-1]["page"],
                    "pages_fetched": len(pages),
                    "rows_fetched": sum(pg["row_count"] for pg in pages),
                },
            },
            "meta": self._meta(first["url"], proxy_url, parser_version="1.2.0"),
            "warnings": crawl_warnings,
        }

    def prewarm_pages(
        self,
        sector_slugs: list[str] | None = None,
        screen_refs: list[dict[str, Any]] | None = None,
        pages_per_target: int = 1,
        proxy_url: str | None = None,
    ) -> dict[str, Any]:
        pages_per_target = max(1, int(pages_per_target))
        sector_slugs = sector_slugs or []
        screen_refs = screen_refs or []

        attempted = 0
        warmed = 0
        failed = 0

        # prewarm sectors
        for slug in sector_slugs:
            links = self._extract_sector_links(self._fetch_html(f"{BASE}/market/", proxy_url=proxy_url))
            canonical_name = SECTOR_ALIAS_TO_SLUG.get(slug)
            if not canonical_name:
                continue
            sector_url = self._resolve_sector_url(canonical_name, links)
            if not sector_url:
                continue
            parsed = urlparse(sector_url)
            base_sector_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            for p in range(1, pages_per_target + 1):
                attempted += 1
                try:
                    self._fetch_html(f"{base_sector_url}?limit=50&page={p}", proxy_url=proxy_url)
                    warmed += 1
                except Exception:
                    failed += 1

        # prewarm screens
        for ref in screen_refs:
            sid = ref.get('screen_id')
            slug = ref.get('slug')
            if not sid or not slug:
                continue
            for p in range(1, pages_per_target + 1):
                attempted += 1
                try:
                    self._fetch_html(f"{BASE}/screens/{sid}/{slug}/?limit=50&page={p}", proxy_url=proxy_url)
                    warmed += 1
                except Exception:
                    failed += 1

        return {
            "data": {
                "attempted_urls": attempted,
                "warmed_urls": warmed,
                "failed_urls": failed,
                "pages_per_target": pages_per_target,
            },
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "parser_version": "1.0.0",
                "proxy_used": bool(proxy_url),
            },
            "warnings": [],
        }

    def _resolve_screen_slug(self, screen_id: int, proxy_url: str | None = None, max_pages: int = 10) -> str | None:
        page = 1
        checked = 0
        total_pages = None

        while True:
            out = self.list_screens(page=page, include_all_pages=False, proxy_url=proxy_url)
            page_data = out.get("data", {}).get("page", {})
            items = page_data.get("items", [])
            for item in items:
                if int(item.get("screen_id", 0)) == int(screen_id):
                    return item.get("slug")

            checked += 1
            if total_pages is None:
                total_pages = page_data.get("pagination", {}).get("total_pages") or 1

            if page >= total_pages or checked >= max_pages:
                break
            page += 1

        return None

    def fetch_screen_details(
        self,
        screen_id: int,
        slug: str,
        page: int = 1,
        limit: int = 50,
        include_all_pages: bool = False,
        proxy_url: str | None = None,
    ) -> dict[str, Any]:
        def _is_valid_screen_page(payload: dict[str, Any]) -> bool:
            title = (payload.get("title") or "").strip().lower()
            if not title:
                return False
            if title in {"register", "login", "page not found", "not found"}:
                return False
            has_query = bool((payload.get("query") or "").strip())
            has_rows = bool(payload.get("row_count", 0) > 0)
            return has_query or has_rows

        def _run_for_slug(active_slug: str) -> tuple[str, str, dict[str, Any], list[dict[str, Any]] | None]:
            base_url = f"{BASE}/screens/{screen_id}/{active_slug}/"

            def _fetch_page(p: int) -> dict[str, Any]:
                page_url = f"{base_url}?limit={limit}&page={p}"
                html = self._fetch_html(page_url, proxy_url=proxy_url)
                tree = HTMLParser(html)

                heading = tree.css_first("h1")
                title = heading.text(separator=" ", strip=True) if heading else None

                query_node = tree.css_first("#query-builder")
                query = query_node.text(separator="\n", strip=True) if query_node else None

                author = None
                owner_profile_url = None
                for pnode in tree.css("p.sub"):
                    txt = pnode.text(separator=" ", strip=True)
                    if txt.lower().startswith("by "):
                        author = txt[3:].strip()
                        a = pnode.css_first("a[href]")
                        if a:
                            href = (a.attributes.get("href") or "").strip()
                            if href:
                                owner_profile_url = urljoin(BASE, href)
                        break

                export_url = None
                export_form = tree.css_first("form[action*='/api/export/screen/']")
                if export_form:
                    action = (export_form.attributes.get("action") or "").strip()
                    if action:
                        export_url = urljoin(BASE, action)

                source_id = None
                sort = None
                order = None
                for inp in tree.css("input[type='hidden']"):
                    name = (inp.attributes.get("name") or "").strip()
                    value = (inp.attributes.get("value") or "").strip()
                    if name == "source_id":
                        source_id = value or None
                    elif name == "sort":
                        sort = value or None
                    elif name == "order":
                        order = value or None

                columns, rows = self._extract_market_rows(tree)
                columns_meta = self._extract_columns_meta(tree)
                current_page, total_pages = self._extract_pagination(tree)
                total_results = self._extract_market_result_count(tree)

                return {
                    "page": p,
                    "url": page_url,
                    "title": title,
                    "author": author,
                    "owner_profile_url": owner_profile_url,
                    "query": query,
                    "export_url": export_url,
                    "source_id": source_id,
                    "sort": sort,
                    "order": order,
                    "columns": columns,
                    "columns_meta": columns_meta,
                    "rows": rows,
                    "row_count": len(rows),
                    "pagination": {
                        "current_page": current_page or p,
                        "total_pages": total_pages,
                        "limit": limit,
                    },
                    "total_results": total_results,
                }

            first = _fetch_page(page)
            if not include_all_pages:
                return active_slug, base_url, first, None, []

            total_pages = first["pagination"].get("total_pages") or 1
            effective_max = min(total_pages, page + self.screens_max_pages_default - 1)
            pages = [first]
            crawl_start = time.monotonic()
            detail_warnings: list[str] = []
            for p in range(page + 1, effective_max + 1):
                if time.monotonic() - crawl_start > self.max_crawl_seconds:
                    detail_warnings.append(f"Crawl stopped after {len(pages)} pages due to {self.max_crawl_seconds}s timeout")
                    break
                pages.append(_fetch_page(p))
            return active_slug, base_url, first, pages, detail_warnings

        active_slug, base_url, first, pages, crawl_warnings = _run_for_slug(slug)

        # stale slug recovery: resolve latest slug from screens list and retry once
        if not _is_valid_screen_page(first):
            resolved = self._resolve_screen_slug(screen_id=screen_id, proxy_url=proxy_url)
            if resolved and resolved != active_slug:
                active_slug, base_url, first, pages, crawl_warnings = _run_for_slug(resolved)

        if not first.get("title"):
            raise ValueError("Screen not found or inaccessible")

        if not include_all_pages:
            return {
                "data": {
                    "screen_id": screen_id,
                    "slug": active_slug,
                    "base_url": base_url,
                    "page": first,
                },
                "meta": self._meta(first["url"], proxy_url, parser_version="1.2.0"),
                "warnings": crawl_warnings,
            }

        pages = pages or [first]
        return {
            "data": {
                "screen_id": screen_id,
                "slug": active_slug,
                "base_url": base_url,
                "pages": pages,
                "summary": {
                    "from_page": page,
                    "to_page": pages[-1]["page"],
                    "pages_fetched": len(pages),
                    "rows_fetched": sum(pg["row_count"] for pg in pages),
                },
            },
            "meta": self._meta(first["url"], proxy_url, parser_version="1.2.0"),
            "warnings": crawl_warnings,
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
