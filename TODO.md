# TODO - Screener Unofficial API

## Phase 13 - Screens discovery hardening

- [x] Add `/v1/screens/pages` endpoint to quickly return total pages + counts without fetching every item page.
- [x] Add dedupe guard when aggregating screens across many pages (by `screen_id`).
- [x] Add optional `max_pages` query param for `/v1/screens?include_all_pages=true` to cap long crawls.
- [x] Add tests covering page 50+ and edge pagination states (missing Next, sparse page links).

## Phase 14 - Screen detail enrichment

- [x] Parse and return extra metadata from screen detail page:
  - [x] created_by / owner profile link
  - [x] export endpoint URL (if present)
  - [x] source_id + sort/order hidden form fields
- [x] Add `columns_meta` where available (tooltips/unit hints from table headers).
- [x] Add tests for enriched metadata extraction.

## Phase 15 - Reliability + performance

- [x] Add optional Redis cache backend for expensive market/screens pages.
- [x] Add per-endpoint throttling knobs for sector/screens crawling.
- [x] Add background prewarm command/script for known sector/screen pages.
- [x] Add retry/backoff around transient upstream failures (429/5xx) with bounded attempts.
- [x] Add tests for retry behavior (without increasing external test flakiness).

## Phase 16 - API UX

- [x] Add endpoint docs section with response examples for:
  - [x] `/v1/sectors`
  - [x] `/v1/sectors/{sector}`
  - [x] `/v1/screens`
  - [x] `/v1/screens/{screen_id}/{slug}`
- [x] Add OpenAPI examples for new query parameters (`include_all_pages`, `limit`, `page`).
- [x] Add `filters` placeholder support for future screen query customization.
