import hashlib
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.api import routes
from app.core.cache import CacheStore
from app.core.config import load_settings
from app.core.rate_limit import allow_request
from app.services.screener_client import ScreenerClient

app = FastAPI(title="Screener Unofficial API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = load_settings()

# Phase 8 runtime security defaults (overridable in tests/runtime)
app.state.api_key = settings.api_key
app.state.rate_limit_per_minute = settings.rate_limit_per_minute
app.state.rate_limit_backend = settings.rate_limit_backend
app.state.redis_url = settings.redis_url
app.state.redis_client = None  # optional; initialize externally when REDIS_URL is used
app.state.rate_buckets = defaultdict(deque)
app.state.metrics = {
    "requests_total": 0,
    "auth_failed_total": 0,
    "rate_limited_total": 0,
}

cache_store = CacheStore(backend=settings.cache_backend, redis_client=app.state.redis_client)
configured_client = ScreenerClient(
    cache_ttl_seconds=settings.cache_ttl_seconds,
    throttle_company_interval_seconds=settings.throttle_company_interval_seconds,
    throttle_sector_interval_seconds=settings.throttle_sector_interval_seconds,
    throttle_screens_interval_seconds=settings.throttle_screens_interval_seconds,
    upstream_max_retries=settings.upstream_max_retries,
    upstream_retry_backoff_seconds=settings.upstream_retry_backoff_seconds,
    cache_store=cache_store,
    screens_max_pages_default=settings.screens_max_pages_default,
    max_crawl_seconds=settings.max_crawl_seconds,
)
routes.configure_client(configured_client)


@app.middleware("http")
async def auth_and_rate_limit_middleware(request: Request, call_next):
    path = request.url.path

    # Skip all middleware for MCP transport (streaming responses break BaseHTTPMiddleware)
    if path.startswith("/mcp"):
        return await call_next(request)

    metrics = getattr(request.app.state, "metrics", None)
    if metrics is None:
        metrics = {"requests_total": 0, "auth_failed_total": 0, "rate_limited_total": 0}
        request.app.state.metrics = metrics
    metrics["requests_total"] = int(metrics.get("requests_total", 0)) + 1

    # Keep docs/openapi/health cheap and accessible
    public_prefixes = ("/docs", "/openapi.json", "/redoc", "/health", "/ready", "/metrics", "/mcp")
    is_public = path.startswith(public_prefixes)

    if not is_public:
        configured_api_key = getattr(request.app.state, "api_key", None)
        if configured_api_key:
            provided = request.headers.get("x-api-key")
            if provided != configured_api_key:
                metrics["auth_failed_total"] = int(metrics.get("auth_failed_total", 0)) + 1
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {"code": "AUTH_REQUIRED", "message": "Valid x-api-key is required"},
                        "detail": "Missing or invalid API key",
                    },
                )

        rate_limit = int(getattr(request.app.state, "rate_limit_per_minute", 120))

        # Best-effort client identity
        client_id = request.client.host if request.client else "unknown"

        allowed = allow_request(request.app.state, client_id)
        if not allowed:
            metrics["rate_limited_total"] = int(metrics.get("rate_limited_total", 0)) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "error": {"code": "RATE_LIMITED", "message": "Rate limit exceeded"},
                    "detail": f"Max {rate_limit} requests per minute",
                },
            )

    return await call_next(request)


@app.middleware("http")
async def etag_cache_middleware(request: Request, call_next):
    """Add ETag and Cache-Control headers to API responses. Returns 304 on ETag match."""
    path = request.url.path

    # Skip for MCP transport (streaming responses break BaseHTTPMiddleware)
    if path.startswith("/mcp"):
        return await call_next(request)

    response = await call_next(request)

    # Only apply to API data endpoints (skip docs, health, metrics)
    if not path.startswith("/v1/"):
        return response

    # Read the response body to compute ETag
    body_chunks = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, str):
            chunk = chunk.encode("utf-8")
        body_chunks.append(chunk)
    body = b"".join(body_chunks)

    if response.status_code == 200 and body:
        etag = f'"{hashlib.sha256(body).hexdigest()[:16]}"'
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match == etag:
            return Response(status_code=304, headers={"ETag": etag})

        return Response(
            content=body,
            status_code=response.status_code,
            headers={
                **dict(response.headers),
                "ETag": etag,
                "Cache-Control": f"public, max-age={settings.cache_ttl_seconds}",
            },
            media_type=response.media_type,
        )

    return Response(
        content=body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
            },
            "detail": exc.errors(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = "BAD_REQUEST" if exc.status_code < 500 else "UPSTREAM_ERROR"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail),
            },
            "detail": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=502,
        content={
            "error": {
                "code": "UPSTREAM_ERROR",
                "message": str(exc),
            },
            "detail": str(exc),
        },
    )


app.include_router(routes.router)

# ── Mount MCP SSE server at /mcp ──────────────────────────────────
try:
    from screener_mcp.server import mcp as mcp_server
    app.mount("/mcp", mcp_server.sse_app())
except ImportError:
    pass
