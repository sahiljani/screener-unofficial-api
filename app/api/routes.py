from typing import Any, Union

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.models.screens import (
    ScreenDetailAllResponse,
    ScreenDetailResponse,
    ScreensListAllResponse,
    ScreensListResponse,
    ScreensPagesResponse,
)
from app.services.screener_client import ScreenerClient

router = APIRouter()
client = ScreenerClient()


def configure_client(new_client: ScreenerClient) -> None:
    global client
    client = new_client


class ScreenRef(BaseModel):
    screen_id: int
    slug: str


class PrewarmRequest(BaseModel):
    sector_slugs: list[str] = Field(default_factory=list)
    screen_refs: list[ScreenRef] = Field(default_factory=list)
    pages_per_target: int = Field(default=1, ge=1, le=10)
    proxy_url: str | None = None

ALLOWED_TABS = {
    "analysis",
    "peers",
    "quarters",
    "profit-loss",
    "balance-sheet",
    "cash-flow",
    "ratios",
    "shareholding",
    "documents",
}

PROXY_URL_QUERY = Query(
    default=None,
    description=(
        "Optional proxy URL for outbound requests. "
        "Format: scheme://[username:password@]host:port "
        "(e.g. http://user:pass@127.0.0.1:8080 or socks5://127.0.0.1:9050)."
    ),
    pattern=r"^(https?|socks5h?|socks4a?)://.+",
    examples=[
        "http://username:password@host:port",
        "https://username:password@host:port",
        "socks5://username:password@host:port",
    ],
)

@router.get("/health")
def health():
    return {"ok": True, "service": "screener-unofficial-api"}


@router.get("/metrics")
def metrics(request: Request):
    m = getattr(request.app.state, "metrics", {})
    return {
        "requests_total": int(m.get("requests_total", 0)),
        "auth_failed_total": int(m.get("auth_failed_total", 0)),
        "rate_limited_total": int(m.get("rate_limited_total", 0)),
    }


@router.get("/ready")
def ready(request: Request):
    backend = getattr(request.app.state, "rate_limit_backend", "memory")
    redis_client = getattr(request.app.state, "redis_client", None)

    checks = {"rate_limit_backend": backend}

    if backend == "redis" and redis_client is None:
        checks["redis"] = "missing_client"
        return JSONResponse(status_code=503, content={"ok": False, "checks": checks})

    if backend == "redis":
        checks["redis"] = "ok"

    return {"ok": True, "checks": checks}


@router.get("/v1/ping")
def ping():
    return {"ok": True, "ping": "pong"}

@router.get("/v1/company/{symbol}")
def get_company(
    symbol: str,
    mode: str = Query(default="consolidated", pattern="^(standalone|consolidated)$"),
    proxy_url: str | None = PROXY_URL_QUERY,
):
    try:
        return client.fetch_company(symbol=symbol, mode=mode, proxy_url=proxy_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/v1/company/{symbol}/raw")
def get_company_raw(
    symbol: str,
    mode: str = Query(default="consolidated", pattern="^(standalone|consolidated)$"),
    proxy_url: str | None = PROXY_URL_QUERY,
):
    try:
        return client.fetch_company_raw(symbol=symbol, mode=mode, proxy_url=proxy_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/v1/company/{symbol}/{tab}")
def get_company_tab(
    symbol: str,
    tab: str,
    mode: str = Query(default="consolidated", pattern="^(standalone|consolidated)$"),
    proxy_url: str | None = PROXY_URL_QUERY,
):
    if tab not in ALLOWED_TABS:
        raise HTTPException(status_code=400, detail=f"Unsupported tab '{tab}'. Allowed: {sorted(ALLOWED_TABS)}")

    try:
        return client.fetch_company_tab(symbol=symbol, tab=tab, mode=mode, proxy_url=proxy_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/v1/compare")
def compare_companies(
    symbols: str = Query(..., description="Comma-separated symbols, e.g. TCS,INFY"),
    mode: str = Query(default="consolidated", pattern="^(standalone|consolidated)$"),
    proxy_url: str | None = PROXY_URL_QUERY,
):
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if len(symbol_list) < 2:
            raise HTTPException(status_code=400, detail="Provide at least 2 symbols")
        return client.compare_companies(symbols=symbol_list, mode=mode, proxy_url=proxy_url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/v1/search/companies")
def search_companies(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
):
    try:
        return client.search_companies(query=q, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/v1/sectors",
    openapi_extra={
        "examples": {
            "listSectors": {
                "summary": "List supported sectors",
                "value": {
                    "data": {
                        "count": 2,
                        "sectors": [
                            {
                                "name": "Pharmaceuticals & Biotechnology",
                                "slug": "pharmaceuticals-biotechnology",
                                "url": "https://www.screener.in/market/IN06/IN0601/IN060101/",
                                "available": True,
                            },
                            {
                                "name": "Aerospace & Defense",
                                "slug": "aerospace-defense",
                                "url": "https://www.screener.in/market/IN07/IN0702/IN070201/IN070201001/",
                                "available": True,
                            },
                        ],
                    },
                    "meta": {
                        "source_url": "https://www.screener.in/market/",
                        "fetched_at": "2026-04-08T00:00:00+00:00",
                        "parser_version": "1.0.0",
                        "proxy_used": False,
                    },
                    "warnings": [],
                },
            }
        }
    },
)
def list_sectors(
    proxy_url: str | None = PROXY_URL_QUERY,
):
    try:
        return client.list_sectors(proxy_url=proxy_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/v1/sectors/{sector}",
    openapi_extra={
        "examples": {
            "sectorSinglePage": {
                "summary": "Single page sector response",
                "value": {
                    "data": {
                        "sector": "Pharmaceuticals & Biotechnology",
                        "slug": "pharmaceuticals-biotechnology",
                        "base_url": "https://www.screener.in/market/IN06/IN0601/IN060101/",
                        "page": {
                            "page": 1,
                            "columns": ["S.No.", "Name", "CMP Rs."],
                            "rows": [["1.", "Sun Pharma.Inds.", "1718.00"]],
                            "row_count": 1,
                            "pagination": {"current_page": 1, "total_pages": 9, "limit": 50},
                        },
                    },
                    "meta": {"parser_version": "1.0.0"},
                    "warnings": [],
                },
            }
        }
    },
)
def get_sector_data(
    sector: str,
    page: int = Query(default=1, ge=1, examples=[1, 2]),
    limit: int = Query(default=50, ge=1, le=50, examples=[10, 25, 50]),
    include_all_pages: bool = Query(default=False, description="When true, fetches all remaining pages from the starting page", examples=[False, True]),
    proxy_url: str | None = PROXY_URL_QUERY,
):
    try:
        return client.fetch_sector_data(
            sector=sector,
            page=page,
            limit=limit,
            include_all_pages=include_all_pages,
            proxy_url=proxy_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/v1/screens",
    response_model=Union[ScreensListResponse, ScreensListAllResponse],
    openapi_extra={
        "examples": {
            "screensSinglePage": {
                "summary": "Screens list on a single page",
                "value": {
                    "data": {
                        "page": {
                            "page": 1,
                            "item_count": 2,
                            "items": [
                                {
                                    "screen_id": 1450832,
                                    "slug": "fibonacci-based-btw-05-and-0786",
                                    "title": "Fibonacci based btw 0.5 and 0.786",
                                }
                            ],
                        },
                        "filters": {
                            "raw": "author:demo",
                            "applied": False,
                            "note": "Filters placeholder is accepted for forward compatibility and currently not applied upstream.",
                        },
                    },
                    "meta": {"parser_version": "1.1.0"},
                    "warnings": [],
                },
            }
        }
    },
)
async def list_screens(
    page: int = Query(default=1, ge=1, examples=[1, 50]),
    include_all_pages: bool = Query(default=False, description="When true, fetches all remaining pages from the starting page", examples=[False, True]),
    max_pages: int | None = Query(default=None, ge=1, description="Optional cap for number of pages fetched when include_all_pages=true", examples=[2, 5]),
    q: str | None = Query(default=None, description="Search screens by title or description (client-side filter on fetched pages). For full search, combine with include_all_pages=true.", examples=["growth", "dividend"]),
    sort: str | None = Query(default=None, description="Sort results: 'title' (alphabetical) or 'screen_id' (numeric/recency)", examples=["title", "screen_id"]),
    order: str | None = Query(default=None, description="Sort order: 'asc' or 'desc'. Defaults to 'asc' for title, 'desc' for screen_id.", examples=["asc", "desc"]),
    filters: str | None = Query(default=None, description="Filter screens: 'has:description', 'id_gt:N', 'id_lt:N'. Unrecognized filters are ignored.", examples=["has:description", "id_gt:100000"]),
    proxy_url: str | None = PROXY_URL_QUERY,
):
    try:
        return await client.async_list_screens(page=page, include_all_pages=include_all_pages, max_pages=max_pages, proxy_url=proxy_url, filters=filters, q=q, sort=sort, order=order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/v1/screens/pages",
    response_model=ScreensPagesResponse,
    deprecated=True,
    description="Deprecated: use GET /v1/screens instead — its pagination field returns the same info.",
)
async def screens_pages(
    page: int = Query(default=1, ge=1),
    proxy_url: str | None = PROXY_URL_QUERY,
):
    try:
        return await client.async_screens_pages(page=page, proxy_url=proxy_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/v1/prewarm")
def prewarm_targets(body: PrewarmRequest):
    try:
        return client.prewarm_pages(
            sector_slugs=body.sector_slugs,
            screen_refs=[r.model_dump() for r in body.screen_refs],
            pages_per_target=body.pages_per_target,
            proxy_url=body.proxy_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/v1/screens/{screen_id}/{slug}",
    response_model=Union[ScreenDetailResponse, ScreenDetailAllResponse],
    openapi_extra={
        "examples": {
            "screenDetails": {
                "summary": "Detailed screen page response",
                "value": {
                    "data": {
                        "screen_id": 1450832,
                        "slug": "fibonacci-based-btw-05-and-0786",
                        "page": {
                            "title": "Fibonacci based btw 0.5 and 0.786",
                            "author": "Laxman",
                            "query": "Current price > 10",
                            "columns": ["S.No.", "Name", "CMP Rs."],
                            "rows": [["1.", "One Point One", "46.92"]],
                        },
                    },
                    "meta": {"parser_version": "1.2.0"},
                    "warnings": [],
                },
            }
        }
    },
)
async def get_screen_details(
    screen_id: int,
    slug: str,
    page: int = Query(default=1, ge=1, examples=[1, 2]),
    limit: int = Query(default=50, ge=1, le=50, examples=[10, 25, 50]),
    include_all_pages: bool = Query(default=False, description="When true, fetches all remaining pages from the starting page", examples=[False, True]),
    proxy_url: str | None = PROXY_URL_QUERY,
):
    try:
        return await client.async_fetch_screen_details(
            screen_id=screen_id,
            slug=slug,
            page=page,
            limit=limit,
            include_all_pages=include_all_pages,
            proxy_url=proxy_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


