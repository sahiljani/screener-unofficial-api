# screener-unofficial-api

Unofficial Python API for Screener-style company + live market data extraction.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open docs: http://127.0.0.1:8000/docs

## Ops endpoints (phase 10)

- `GET /health` → liveness
- `GET /ready` → readiness (checks rate-limit backend wiring)
- `GET /v1/ping` → authenticated/rate-limited ping

## Core company endpoints

- `GET /health`
- `GET /v1/company/{symbol}`
- `GET /v1/company/{symbol}/raw`
- `GET /v1/company/{symbol}/{tab}`
  - `analysis`
  - `peers`
  - `quarters`
  - `profit-loss`
  - `balance-sheet`
  - `cash-flow`
  - `ratios`
  - `shareholding`
  - `documents`
  - `insights`
- `GET /v1/compare?symbols=TCS,INFY`
- `GET /v1/search/companies?q=tata&limit=10`

Optional query params on company endpoints:
- `mode=standalone|consolidated` (default: consolidated)
- `proxy_url=<scheme://user:pass@host:port>` (optional)


## Error contract (phase 6)

All errors return a normalized envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR|BAD_REQUEST|UPSTREAM_ERROR",
    "message": "..."
  },
  "detail": "..."
}
```

Validation issues are normalized to HTTP `400`.

## Security & rate limiting (phase 8)

- Optional API key auth using `x-api-key` header.
- Rate limiting backends:
  - `memory` (default)
  - `redis` (client wiring can be initialized externally)

Environment-driven config:
- `API_KEY` (optional)
- `RATE_LIMIT_PER_MINUTE` (default `120`)
- `RATE_LIMIT_BACKEND` (`memory|redis`, default `memory`)
- `REDIS_URL` (optional)

If `api_key` is configured and missing/invalid:
- `401` with `error.code = AUTH_REQUIRED`

If rate limit is exceeded:
- `429` with `error.code = RATE_LIMITED`

## Docker (phase 9)

Build and run locally:

```bash
docker compose up --build
```

API: `http://127.0.0.1:8000`
Docs: `http://127.0.0.1:8000/docs`
