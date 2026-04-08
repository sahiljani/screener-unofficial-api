from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from app.services.screener_client import ScreenerClient

router = APIRouter()
client = ScreenerClient()

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


@router.get("/v1/sectors")
def list_sectors(
    proxy_url: str | None = PROXY_URL_QUERY,
):
    try:
        return client.list_sectors(proxy_url=proxy_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/v1/sectors/{sector}")
def get_sector_data(
    sector: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=50),
    include_all_pages: bool = Query(default=False, description="When true, fetches all remaining pages from the starting page"),
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


@router.get("/v1/screens")
def list_screens(
    page: int = Query(default=1, ge=1),
    include_all_pages: bool = Query(default=False, description="When true, fetches all remaining pages from the starting page"),
    proxy_url: str | None = PROXY_URL_QUERY,
):
    try:
        return client.list_screens(page=page, include_all_pages=include_all_pages, proxy_url=proxy_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/v1/screens/{screen_id}/{slug}")
def get_screen_details(
    screen_id: int,
    slug: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=50),
    include_all_pages: bool = Query(default=False, description="When true, fetches all remaining pages from the starting page"),
    proxy_url: str | None = PROXY_URL_QUERY,
):
    try:
        return client.fetch_screen_details(
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


