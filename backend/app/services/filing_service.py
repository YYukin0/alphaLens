import math
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.config import Settings
from app.core.logging import get_logger
from app.models.filing import Filing
from app.repositories.filing_repository import FilingRepository
from app.services.company_service import CompanyService
from app.services.event_service import EventService
from app.services.filing_document_service import (
    looks_like_untrimmed_filing_content,
    looks_like_xbrl_text,
    normalize_filing_narrative_text,
)
from app.services.filing_section_service import (
    deserialize_reader_document,
    parse_filing_reader_document,
    serialize_reader_document,
)
from app.services.sec_service import SECService

logger = get_logger(__name__)


@dataclass
class FilingSyncResult:
    synced_count: int
    extraction_queued: int


@dataclass
class FilingHistoricalSyncResult:
    discovered_count: int
    metadata_upserted: int
    content_synced: int
    skipped_existing: int
    extraction_queued: int
    total_count: int
    earliest_filing_date: date | None
    latest_filing_date: date | None
    counts_by_type: dict[str, int]


@dataclass
class FilingStats:
    ticker: str
    total_count: int
    earliest_filing_date: date | None
    latest_filing_date: date | None
    counts_by_type: dict[str, int]


@dataclass
class PaginatedFilings:
    items: list[Filing]
    page: int
    page_size: int
    total_count: int
    total_pages: int
    stats: FilingStats


class FilingService:
    def __init__(
        self,
        db: Session,
        sec_service: SECService,
        company_service: CompanyService,
        settings: Settings,
        event_service: EventService | None = None,
    ) -> None:
        self.repo = FilingRepository(db)
        self.sec_service = sec_service
        self.company_service = company_service
        self.settings = settings
        self.event_service = event_service

    def _needs_resync(self, filing: Filing) -> bool:
        if not filing.extracted_text:
            return True
        if filing.raw_html and not filing.sections_data:
            return True
        if looks_like_xbrl_text(filing.extracted_text):
            return True
        if looks_like_untrimmed_filing_content(filing.extracted_text, filing.filing_type):
            return True
        return False

    def _parse_and_store_sections(self, filing: Filing) -> None:
        document = parse_filing_reader_document(
            raw_html=filing.raw_html,
            extracted_text=filing.extracted_text,
            raw_content=filing.raw_content,
            filing_type=filing.filing_type,
        )
        filing.sections_data = serialize_reader_document(document)
        logger.info(
            "filing_sections_parsed",
            accession_number=filing.accession_number,
            section_count=len(document.sections),
            has_cover_page=document.cover_page is not None,
        )

    def _ensure_reader_sections(self, filing: Filing, persist: bool = False) -> None:
        cached = deserialize_reader_document(filing.sections_data)
        if cached and cached.sections:
            return
        if not filing.raw_html and not filing.extracted_text and not filing.raw_content:
            return
        self._parse_and_store_sections(filing)
        if persist:
            self.repo.update(filing)

    async def _upsert_filing_metadata(self, company_id: int, sec_filing) -> tuple[Filing, bool]:
        existing = self.repo.get_by_accession_number(sec_filing.accession_number)
        if existing:
            existing.filing_type = sec_filing.filing_type
            existing.filing_date = sec_filing.filing_date
            existing.sec_url = sec_filing.sec_url
            self.repo.update(existing)
            return existing, False

        filing = Filing(
            company_id=company_id,
            filing_type=sec_filing.filing_type,
            filing_date=sec_filing.filing_date,
            accession_number=sec_filing.accession_number,
            sec_url=sec_filing.sec_url,
        )
        self.repo.create(filing)
        return filing, True

    async def _download_filing_content(self, company, filing: Filing, sec_filing) -> bool:
        if not self._needs_resync(filing):
            return False

        try:
            content = await self.sec_service.download_primary_filing(
                cik=company.cik,
                accession_number=sec_filing.accession_number,
                filing_type=sec_filing.filing_type,
                fallback_primary=sec_filing.primary_document,
            )
        except Exception as exc:
            logger.warning(
                "filing_content_download_failed",
                accession_number=sec_filing.accession_number,
                error=str(exc),
            )
            return False

        filing.sec_url = content.sec_url
        filing.raw_html = content.raw_html
        filing.extracted_text = content.extracted_text
        filing.raw_content = content.extracted_text
        self._parse_and_store_sections(filing)
        self.repo.update(filing)
        return True

    def _build_stats(self, ticker: str, company_id: int, filing_type: str | None = None) -> FilingStats:
        total_count = self.repo.count_by_company(company_id, filing_type)
        earliest, latest = self.repo.get_date_range(company_id, filing_type)
        counts_by_type = self.repo.count_by_type(company_id)
        if filing_type:
            normalized = filing_type.upper()
            counts_by_type = {normalized: counts_by_type.get(normalized, 0)}
        return FilingStats(
            ticker=ticker.upper(),
            total_count=total_count,
            earliest_filing_date=earliest,
            latest_filing_date=latest,
            counts_by_type=counts_by_type,
        )

    async def sync_filings_for_ticker(self, ticker: str, limit: int | None = None) -> FilingSyncResult:
        limit = limit or self.settings.max_filings_per_sync
        company = await self.company_service.get_or_create_company(ticker)

        sec_filings = await self.sec_service.get_recent_filings(
            cik=company.cik,
            filing_types=self.settings.filing_types,
            limit=limit,
        )

        synced = 0
        for sec_filing in sec_filings:
            filing, _ = await self._upsert_filing_metadata(company.id, sec_filing)
            if await self._download_filing_content(company, filing, sec_filing):
                synced += 1

        extraction_queued = 0
        if self.event_service and self.settings.auto_extract_events:
            extraction_queued = self.event_service.queue_pending_extractions_for_company(company.id)

        return FilingSyncResult(synced_count=synced, extraction_queued=extraction_queued)

    async def sync_historical_filings_for_ticker(
        self,
        ticker: str,
        years: int | None = None,
        download_content: bool = False,
    ) -> FilingHistoricalSyncResult:
        years = years or self.settings.historical_filing_years
        company = await self.company_service.get_or_create_company(ticker)

        sec_filings = await self.sec_service.get_historical_filings(
            cik=company.cik,
            filing_types=self.settings.filing_types,
            years=years,
        )

        metadata_upserted = 0
        content_synced = 0
        skipped_existing = 0

        for sec_filing in sec_filings:
            filing, created = await self._upsert_filing_metadata(company.id, sec_filing)
            if created:
                metadata_upserted += 1

            if not download_content:
                continue

            if not self._needs_resync(filing):
                skipped_existing += 1
                continue

            if await self._download_filing_content(company, filing, sec_filing):
                content_synced += 1

        extraction_queued = 0
        if self.event_service and self.settings.auto_extract_events:
            extraction_queued = self.event_service.queue_pending_extractions_for_company(company.id)

        stats = self._build_stats(ticker, company.id)
        return FilingHistoricalSyncResult(
            discovered_count=len(sec_filings),
            metadata_upserted=metadata_upserted,
            content_synced=content_synced,
            skipped_existing=skipped_existing,
            extraction_queued=extraction_queued,
            total_count=stats.total_count,
            earliest_filing_date=stats.earliest_filing_date,
            latest_filing_date=stats.latest_filing_date,
            counts_by_type=stats.counts_by_type,
        )

    async def sync_pending_filing_content_for_ticker(
        self,
        ticker: str,
        limit: int | None = None,
    ) -> FilingSyncResult:
        company = self.company_service.get_company_by_ticker(ticker)
        if not company:
            raise ValueError(f"Company '{ticker.upper()}' not found")

        pending = self.repo.list_missing_content(company.id, limit=limit)
        synced = 0
        for filing in pending:
            sec_filing = type(
                "SecFilingStub",
                (),
                {
                    "accession_number": filing.accession_number,
                    "filing_type": filing.filing_type,
                    "primary_document": filing.sec_url.rsplit("/", 1)[-1],
                },
            )()
            if await self._download_filing_content(company, filing, sec_filing):
                synced += 1

        extraction_queued = 0
        if self.event_service and self.settings.auto_extract_events:
            extraction_queued = self.event_service.queue_pending_extractions_for_company(company.id)

        return FilingSyncResult(synced_count=synced, extraction_queued=extraction_queued)

    def get_filing_by_id(self, filing_id: int) -> Filing | None:
        return self.repo.get_by_id(filing_id)

    def get_filing_detail(self, filing_id: int) -> Filing | None:
        filing = self.repo.get_by_id_with_company(filing_id)
        if not filing:
            return None

        normalized_text = normalize_filing_narrative_text(
            extracted_text=filing.extracted_text,
            raw_content=filing.raw_content,
            raw_html=filing.raw_html,
            filing_type=filing.filing_type,
        )
        if normalized_text:
            filing.extracted_text = normalized_text
            filing.raw_content = normalized_text

        self._ensure_reader_sections(filing, persist=True)
        return filing

    def get_filing_stats(self, ticker: str, filing_type: str | None = None) -> FilingStats | None:
        company = self.company_service.get_company_by_ticker(ticker)
        if not company:
            return None
        return self._build_stats(ticker, company.id, filing_type)

    def list_filings_by_ticker(
        self,
        ticker: str,
        filing_type: str | None = None,
        page: int = 1,
        page_size: int | None = None,
    ) -> PaginatedFilings | None:
        company = self.company_service.get_company_by_ticker(ticker)
        if not company:
            return None

        page_size = page_size or self.settings.default_filing_page_size
        page = max(page, 1)
        skip = (page - 1) * page_size
        total_count = self.repo.count_by_company(company.id, filing_type)
        total_pages = max(1, math.ceil(total_count / page_size)) if total_count else 0
        items = self.repo.list_by_company(company.id, filing_type, skip, page_size)
        stats = self._build_stats(ticker, company.id, filing_type)

        return PaginatedFilings(
            items=items,
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            stats=stats,
        )
