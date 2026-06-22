from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class FilingSectionResponse(BaseModel):
    item_key: str
    title: str
    anchor_id: str
    content_html: str
    content_text: str
    order: int


class FilingCoverPageResponse(BaseModel):
    content_html: str
    content_text: str


class FilingReaderResponse(BaseModel):
    parser_version: int = 1
    cover_page: FilingCoverPageResponse | None = None
    sections: list[FilingSectionResponse] = Field(default_factory=list)


class FilingBase(BaseModel):
    filing_type: str
    filing_date: date
    accession_number: str
    sec_url: str


class FilingResponse(FilingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    created_at: datetime


class FilingDetailResponse(FilingResponse):
    raw_html: str | None = None
    extracted_text: str | None = None
    raw_content: str | None = None
    reader: FilingReaderResponse | None = None
    company_name: str | None = None
    ticker: str | None = None


class FilingStatsResponse(BaseModel):
    ticker: str
    total_count: int
    earliest_filing_date: date | None = None
    latest_filing_date: date | None = None
    counts_by_type: dict[str, int] = Field(default_factory=dict)


class PaginatedFilingsResponse(BaseModel):
    items: list[FilingResponse]
    page: int
    page_size: int
    total_count: int
    total_pages: int
    stats: FilingStatsResponse


class FilingSyncRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16, examples=["AAPL"])
    limit: int = Field(default=10, ge=1, le=50)


class FilingHistoricalSyncRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16, examples=["GOOG"])
    years: int = Field(default=10, ge=1, le=30)


class FilingSyncResponse(BaseModel):
    ticker: str
    synced_count: int
    extraction_queued: int = 0
    message: str


class FilingHistoricalSyncResponse(BaseModel):
    ticker: str
    discovered_count: int
    metadata_upserted: int
    content_synced: int
    skipped_existing: int
    extraction_queued: int
    total_count: int
    earliest_filing_date: date | None = None
    latest_filing_date: date | None = None
    counts_by_type: dict[str, int] = Field(default_factory=dict)
    message: str
