# screener-unofficial-api

Unofficial FastAPI for Screener company fundamentals — clean, structured, and developer-ready.

> ⚠️ **Disclaimer**
> - This is an **unofficial** API and is **not affiliated with, endorsed by, or supported by Screener.in**.
> - Use responsibly and ensure your usage complies with Screener’s Terms of Service, robots policies, and applicable laws.
> - This project may break if Screener changes site structure/endpoints.

---

## Clone

```bash
git clone https://github.com/sahiljani/screener-unofficial-api.git
cd screener-unofficial-api
```

---

## Run locally (recommended)

### 1) Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment (optional)

```bash
cp .env.example .env
```

You can leave `.env` empty for default behavior.

### 4) Start API

```bash
uvicorn app.main:app --reload --port 8000
```

Open:
- API docs: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

---

## Docker run

```bash
docker compose up --build
```

Open:
- API docs: http://127.0.0.1:8000/docs

---

## Core endpoints

### Health / Ops
- `GET /health` → liveness
- `GET /ready` → readiness (checks backend wiring)
- `GET /metrics` → basic counters
- `GET /v1/ping` → authenticated/rate-limited ping

### Company data
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

Optional query params on company routes:
- `mode=standalone|consolidated` (default: `consolidated`)
- `proxy_url=<scheme://user:pass@host:port>`

---

## Quick examples

```bash
# Full company snapshot
curl "http://127.0.0.1:8000/v1/company/TCS"

# Single tab
curl "http://127.0.0.1:8000/v1/company/TCS/ratios"

# Compare two symbols
curl "http://127.0.0.1:8000/v1/compare?symbols=TCS,INFY"

# Search companies
curl "http://127.0.0.1:8000/v1/search/companies?q=tata&limit=5"
```

---

## Error format

All errors use a normalized envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR|BAD_REQUEST|UPSTREAM_ERROR|AUTH_REQUIRED|RATE_LIMITED",
    "message": "..."
  },
  "detail": "..."
}
```

---

## Security & rate limiting

- Optional API key auth via `x-api-key`
- Rate limit backends:
  - `memory` (default)
  - `redis` (if configured)

Environment variables:
- `API_KEY` (optional)
- `RATE_LIMIT_PER_MINUTE` (default: `120`)
- `RATE_LIMIT_BACKEND` (`memory|redis`, default: `memory`)
- `REDIS_URL` (optional)

---

## Run tests

```bash
source .venv/bin/activate
pytest -q
```

---

## CI

GitHub Actions workflow runs pytest on push/PR.
