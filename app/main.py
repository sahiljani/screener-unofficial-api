from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import load_settings
from app.core.rate_limit import allow_request

app = FastAPI(title="Screener Unofficial API", version="0.1.0")

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


@app.middleware("http")
async def auth_and_rate_limit_middleware(request: Request, call_next):
    path = request.url.path

    metrics = getattr(request.app.state, "metrics", None)
    if metrics is None:
        metrics = {"requests_total": 0, "auth_failed_total": 0, "rate_limited_total": 0}
        request.app.state.metrics = metrics
    metrics["requests_total"] = int(metrics.get("requests_total", 0)) + 1

    # Keep docs/openapi/health cheap and accessible
    public_prefixes = ("/docs", "/openapi.json", "/redoc", "/health", "/ready", "/metrics")
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


app.include_router(router)
