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
- `GET /v1/compare?symbols=TCS,INFY`
- `GET /v1/search/companies?q=tata&limit=10`

### Sectors / Market data
- `GET /v1/sectors`
  - Lists supported top-level sectors (slug + Screener market URL when available)
- `GET /v1/sectors/{sector}`
  - Returns paginated table data for a sector market page
  - Query params:
    - `page` (default: `1`)
    - `limit` (default: `50`, max: `50`)
    - `include_all_pages` (`true|false`, default: `false`)
      - if `true`, fetches every page from `page` to last page and returns all rows

### Screens data
- `GET /v1/screens/pages`
  - Lightweight page metadata endpoint (current page, total pages, count on page)
- `GET /v1/screens`
  - Lists Screener public screens for a given page
  - Query params:
    - `page` (default: `1`)
    - `include_all_pages` (`true|false`, default: `false`)
      - if `true`, fetches every page from `page` to last page and returns all screens
    - `max_pages` (optional, >= `1`)
      - cap total fetched pages when `include_all_pages=true`
  - Includes cross-page de-duplication by `screen_id`.
- `GET /v1/screens/{screen_id}/{slug}`
  - Returns detailed data for one screen (query + table + pagination)
  - Includes enriched metadata when available:
    - `owner_profile_url`
    - `export_url`
    - `source_id`, `sort`, `order`
    - `columns_meta` (header tooltip/unit hints)
  - Query params:
    - `page` (default: `1`)
    - `limit` (default: `50`, max: `50`)
    - `include_all_pages` (`true|false`, default: `false`)
      - if `true`, fetches every page from `page` to last page and returns all rows

Optional query params on company routes:
- `mode=standalone|consolidated` (default: `consolidated`)
- `proxy_url` (string | null)
  - Format: `<scheme>://[username:password@]host:port`
  - Allowed schemes: `http`, `https`, `socks4`, `socks4a`, `socks5`, `socks5h`
  - Examples:
    - `proxy_url=http://username:password@host:port`
    - `proxy_url=https://username:password@host:port`
    - `proxy_url=socks5://username:password@host:port`

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

# List sectors
curl "http://127.0.0.1:8000/v1/sectors"

# Sector page data (single page)
curl "http://127.0.0.1:8000/v1/sectors/pharmaceuticals-biotechnology?limit=50&page=1"

# Sector page data (all pages)
curl "http://127.0.0.1:8000/v1/sectors/pharmaceuticals-biotechnology?limit=50&page=1&include_all_pages=true"

# Screens pages metadata
curl "http://127.0.0.1:8000/v1/screens/pages?page=50"

# Screens list (single page)
curl "http://127.0.0.1:8000/v1/screens?page=50"

# Screens list (all pages from page 1)
curl "http://127.0.0.1:8000/v1/screens?page=1&include_all_pages=true"

# Screens list (all pages with cap)
curl "http://127.0.0.1:8000/v1/screens?page=1&include_all_pages=true&max_pages=5"

# Screen details (single page)
curl "http://127.0.0.1:8000/v1/screens/1450832/fibonacci-based-btw-05-and-0786?page=1&limit=50"

# Screen details (all pages)
curl "http://127.0.0.1:8000/v1/screens/1450832/fibonacci-based-btw-05-and-0786?page=1&limit=50&include_all_pages=true"
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
