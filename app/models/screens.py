"""Pydantic response models for screens endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Shared ──────────────────────────────────────────────────────────

class Meta(BaseModel):
    source_url: str
    fetched_at: str
    parser_version: str
    proxy_used: bool


# ── /v1/screens (list) ─────────────────────────────────────────────

class ScreenItem(BaseModel):
    screen_id: int
    slug: str
    title: str
    description: str | None = None
    url: str


class ScreensPagination(BaseModel):
    current_page: int
    total_pages: int | None = None


class ScreensPageData(BaseModel):
    page: int
    url: str
    heading: str
    items: list[ScreenItem]
    item_count: int
    pagination: ScreensPagination


class FiltersInfo(BaseModel):
    raw: str | None = None
    applied: bool = False
    note: str


class SearchInfo(BaseModel):
    query: str
    matched: int


class ScreensListData(BaseModel):
    page: ScreensPageData
    filters: FiltersInfo
    search: SearchInfo | None = None


class ScreensListResponse(BaseModel):
    data: ScreensListData
    meta: Meta
    warnings: list[str] = Field(default_factory=list)


class ScreensListSummary(BaseModel):
    from_page: int
    to_page: int
    pages_fetched: int
    screens_fetched: int
    duplicates_skipped: int
    max_pages_applied: bool


class ScreensListAllData(BaseModel):
    pages: list[ScreensPageData]
    summary: ScreensListSummary
    filters: FiltersInfo
    search: SearchInfo | None = None


class ScreensListAllResponse(BaseModel):
    data: ScreensListAllData
    meta: Meta
    warnings: list[str] = Field(default_factory=list)


# ── /v1/screens/pages ──────────────────────────────────────────────

class ScreensPagesInfo(BaseModel):
    page: int
    url: str
    current_page: int | None = None
    total_pages: int | None = None
    screens_on_page: int


class ScreensPagesData(BaseModel):
    page: ScreensPagesInfo


class ScreensPagesResponse(BaseModel):
    data: ScreensPagesData
    meta: Meta
    warnings: list[str] = Field(default_factory=list)


# ── /v1/screens/{screen_id}/{slug} (details) ──────────────────────

class ColumnMeta(BaseModel):
    index: int
    name: str
    tooltip: str | None = None
    title: str | None = None
    unit: str | None = None


class DetailPagination(BaseModel):
    current_page: int
    total_pages: int | None = None
    limit: int


class ScreenDetailPage(BaseModel):
    page: int
    url: str
    title: str | None = None
    author: str | None = None
    owner_profile_url: str | None = None
    query: str | None = None
    export_url: str | None = None
    source_id: str | None = None
    sort: str | None = None
    order: str | None = None
    columns: list[str] = Field(default_factory=list)
    columns_meta: list[ColumnMeta] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    row_count: int = 0
    pagination: DetailPagination
    total_results: int | None = None


class ScreenDetailData(BaseModel):
    screen_id: int
    slug: str
    base_url: str
    page: ScreenDetailPage


class ScreenDetailResponse(BaseModel):
    data: ScreenDetailData
    meta: Meta
    warnings: list[str] = Field(default_factory=list)


class ScreenDetailSummary(BaseModel):
    from_page: int
    to_page: int
    pages_fetched: int
    rows_fetched: int


class ScreenDetailAllData(BaseModel):
    screen_id: int
    slug: str
    base_url: str
    pages: list[ScreenDetailPage]
    summary: ScreenDetailSummary


class ScreenDetailAllResponse(BaseModel):
    data: ScreenDetailAllData
    meta: Meta
    warnings: list[str] = Field(default_factory=list)
