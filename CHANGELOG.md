# Changelog

## v0.10.0

- Added test fixture to reset app state between tests.
- Added GitHub Actions CI workflow running pytest.

## v0.10.1

- Removed NSE market endpoints and related market-specific tests.
- Kept API focused on Screener company/fundamental data endpoints.

## v0.11.0

- Company endpoint response updated:
  - removed `insights`
  - added structured `analysis`
  - added structured `peers` (including dynamic peers fetch)
- Added sectors endpoints:
  - `GET /v1/sectors`
  - `GET /v1/sectors/{sector}` with pagination and `include_all_pages`

## v0.12.0

- Added screens endpoints:
  - `GET /v1/screens`
  - `GET /v1/screens/{screen_id}/{slug}`
- Added pagination + `include_all_pages` support for screens list and screen details.
- Added TDD coverage for screens service and API routes.
