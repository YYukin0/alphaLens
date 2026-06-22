from dataclasses import dataclass
from datetime import date, timedelta

import httpx

from app.config import Settings
from app.core.logging import get_logger
from app.services.filing_document_service import (
    FilingIndexItem,
    FilingTextExtractor,
    analyze_xbrl_text,
    is_xbrl_attachment,
    log_extraction_diagnostics,
    log_xbrl_rejection_diagnostics,
    normalize_index_items,
    select_primary_document,
)

logger = get_logger(__name__)


@dataclass
class SECCompanyInfo:
    ticker: str
    company_name: str
    cik: str


@dataclass
class SECFilingInfo:
    filing_type: str
    filing_date: date
    accession_number: str
    sec_url: str
    primary_document: str


@dataclass
class SECFilingContent:
    sec_url: str
    primary_document: str
    raw_html: str
    extracted_text: str


class SECService:
    """Client for SEC EDGAR APIs."""

    TICKER_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    SUBMISSIONS_FILE_URL = "https://data.sec.gov/submissions/{filename}"
    ARCHIVE_BASE = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{filename}"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.headers = {
            "User-Agent": settings.sec_user_agent,
            "Accept-Encoding": "gzip, deflate",
        }
        self.text_extractor = FilingTextExtractor()

    async def lookup_ticker(self, ticker: str) -> SECCompanyInfo | None:
        ticker = ticker.upper().strip()
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            response = await client.get(self.TICKER_CIK_URL)
            response.raise_for_status()
            data = response.json()

        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker:
                cik = str(entry["cik_str"]).lstrip("0") or "0"
                return SECCompanyInfo(
                    ticker=ticker,
                    company_name=entry.get("title", ticker),
                    cik=cik,
                )
        return None

    async def _fetch_json(self, url: str, timeout: float = 60.0) -> dict:
        async with httpx.AsyncClient(headers=self.headers, timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def fetch_submissions(self, cik: str) -> dict:
        normalized_cik = cik.zfill(10)
        url = self.SUBMISSIONS_URL.format(cik=normalized_cik)
        return await self._fetch_json(url)

    async def fetch_submissions_file(self, filename: str) -> dict:
        url = self.SUBMISSIONS_FILE_URL.format(filename=filename)
        return await self._fetch_json(url)

    @staticmethod
    def _parse_filing_batch(
        batch: dict,
        cik: str,
        filing_types: list[str],
    ) -> list[SECFilingInfo]:
        forms = batch.get("form", [])
        filing_dates = batch.get("filingDate", [])
        accession_numbers = batch.get("accessionNumber", [])
        primary_documents = batch.get("primaryDocument", [])
        allowed = {filing_type.upper() for filing_type in filing_types}

        filings: list[SECFilingInfo] = []
        for idx, form in enumerate(forms):
            normalized_form = form.upper()
            if normalized_form not in allowed:
                continue

            accession = accession_numbers[idx]
            primary_doc = primary_documents[idx]
            sec_url = SECService.build_archive_url_static(cik, accession, primary_doc)

            filings.append(
                SECFilingInfo(
                    filing_type=normalized_form,
                    filing_date=date.fromisoformat(filing_dates[idx]),
                    accession_number=accession,
                    sec_url=sec_url,
                    primary_document=primary_doc,
                )
            )
        return filings

    @staticmethod
    def build_archive_url_static(cik: str, accession_number: str, filename: str) -> str:
        accession_no_dashes = accession_number.replace("-", "")
        return SECService.ARCHIVE_BASE.format(
            cik=cik.lstrip("0") or "0",
            accession_no_dashes=accession_no_dashes,
            filename=filename,
        )

    async def get_historical_filings(
        self,
        cik: str,
        filing_types: list[str] | None = None,
        years: int | None = None,
    ) -> list[SECFilingInfo]:
        """Merge filings.recent and archive submission files, deduplicated by accession."""
        filing_types = filing_types or self.settings.filing_types
        years = years or self.settings.historical_filing_years
        cutoff = date.today() - timedelta(days=years * 365)

        submissions = await self.fetch_submissions(cik)
        filings_by_accession: dict[str, SECFilingInfo] = {}

        def merge_batch(batch: dict) -> None:
            for filing in self._parse_filing_batch(batch, cik, filing_types):
                filings_by_accession[filing.accession_number] = filing

        merge_batch(submissions.get("filings", {}).get("recent", {}))

        archive_files = submissions.get("filings", {}).get("files", [])
        archives_loaded = 0
        for archive_meta in archive_files:
            if filings_by_accession:
                earliest = min(item.filing_date for item in filings_by_accession.values())
                if earliest <= cutoff:
                    break

            archive_data = await self.fetch_submissions_file(archive_meta["name"])
            merge_batch(archive_data)
            archives_loaded += 1

        all_filings = list(filings_by_accession.values())
        if not all_filings:
            return []

        earliest_available = min(item.filing_date for item in all_filings)
        if earliest_available > cutoff:
            filtered = all_filings
        else:
            filtered = [item for item in all_filings if item.filing_date >= cutoff]

        filtered.sort(key=lambda item: item.filing_date, reverse=True)
        logger.info(
            "sec_historical_filings_fetched",
            cik=cik,
            count=len(filtered),
            earliest=min(item.filing_date for item in filtered).isoformat(),
            latest=max(item.filing_date for item in filtered).isoformat(),
            archive_files_loaded=archives_loaded,
        )
        return filtered

    async def get_recent_filings(
        self,
        cik: str,
        filing_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[SECFilingInfo]:
        filing_types = filing_types or self.settings.filing_types
        submissions = await self.fetch_submissions(cik)
        recent = submissions.get("filings", {}).get("recent", {})
        filings = self._parse_filing_batch(recent, cik, filing_types)

        logger.info(
            "sec_filings_fetched",
            cik=cik,
            count=min(len(filings), limit),
            filing_types=filing_types,
        )
        return filings[:limit]

    def build_archive_url(self, cik: str, accession_number: str, filename: str) -> str:
        return self.build_archive_url_static(cik, accession_number, filename)

    async def fetch_filing_index(self, cik: str, accession_number: str) -> list[FilingIndexItem]:
        accession_no_dashes = accession_number.replace("-", "")
        index_url = self.ARCHIVE_BASE.format(
            cik=cik.lstrip("0") or "0",
            accession_no_dashes=accession_no_dashes,
            filename="index.json",
        )

        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            response = await client.get(index_url)
            response.raise_for_status()
            payload = response.json()

        items = normalize_index_items(payload)
        logger.info(
            "sec_filing_index_fetched",
            accession_number=accession_number,
            item_count=len(items),
        )
        return items

    async def download_primary_filing(
        self,
        cik: str,
        accession_number: str,
        filing_type: str,
        fallback_primary: str | None = None,
    ) -> SECFilingContent:
        content, _ = await self.inspect_primary_filing(
            cik=cik,
            accession_number=accession_number,
            filing_type=filing_type,
            fallback_primary=fallback_primary,
            raise_on_xbrl=True,
        )
        return content

    async def inspect_primary_filing(
        self,
        cik: str,
        accession_number: str,
        filing_type: str,
        fallback_primary: str | None = None,
        raise_on_xbrl: bool = False,
    ) -> tuple[SECFilingContent | None, dict]:
        index_items = await self.fetch_filing_index(cik, accession_number)
        primary_document = select_primary_document(index_items, filing_type, fallback_primary)
        sec_url = self.build_archive_url(cik, accession_number, primary_document)

        raw_html = await self.download_filing_content(sec_url)
        extracted_text, parser_diagnostics = self.text_extractor.extract_with_diagnostics(
            raw_html,
            filing_type=filing_type,
        )
        log_extraction_diagnostics(
            accession_number=accession_number,
            selected_document=primary_document,
            filing_type=filing_type,
            diagnostics=parser_diagnostics,
        )
        xbrl_analysis = analyze_xbrl_text(extracted_text, top_token_count=50)

        diagnostics = {
            "accession_number": accession_number,
            "sec_url": sec_url,
            "selected_document": primary_document,
            "raw_html_preview": raw_html[:1000],
            "raw_html_length": len(raw_html),
            "extracted_text_preview": xbrl_analysis.preview_1000,
            "extracted_text_preview_3000": parser_diagnostics.preview_3000,
            "extracted_text_preview_5000": (
                parser_diagnostics.final_text_slices.preview_5000
                if parser_diagnostics.final_text_slices
                else extracted_text[:5000]
            ),
            "extracted_text_length": len(extracted_text),
            "xbrl_ratio": xbrl_analysis.xbrl_token_ratio,
            "xbrl_analysis": xbrl_analysis.to_dict(),
            "parser_diagnostics": parser_diagnostics.to_dict(),
            "index_candidates": [
                {
                    "name": item.name,
                    "type": item.doc_type,
                    "size": item.size,
                    "is_html": item.name.lower().endswith((".htm", ".html")),
                    "is_xbrl_attachment": is_xbrl_attachment(item.name),
                }
                for item in index_items
            ],
        }

        if xbrl_analysis.is_xbrl:
            log_xbrl_rejection_diagnostics(
                accession_number=accession_number,
                selected_document=primary_document,
                extracted_text=extracted_text,
                parser_diagnostics=parser_diagnostics,
            )
            if raise_on_xbrl:
                raise ValueError(
                    f"Extracted filing text for {accession_number} still looks like XBRL; "
                    f"selected document={primary_document}; "
                    f"reasons={'; '.join(xbrl_analysis.reasons)}"
                )
            return None, diagnostics

        logger.info(
            "sec_primary_filing_downloaded",
            accession_number=accession_number,
            primary_document=primary_document,
            html_size=len(raw_html),
            text_size=len(extracted_text),
            xbrl_token_ratio=xbrl_analysis.xbrl_token_ratio,
        )

        content = SECFilingContent(
            sec_url=sec_url,
            primary_document=primary_document,
            raw_html=raw_html,
            extracted_text=extracted_text,
        )
        return content, diagnostics

    async def download_filing_content(self, sec_url: str) -> str:
        async with httpx.AsyncClient(headers=self.headers, timeout=60.0) as client:
            response = await client.get(sec_url)
            response.raise_for_status()
            content = response.text

        logger.info("filing_content_downloaded", url=sec_url, size=len(content))
        return content

    @staticmethod
    def strip_html(html: str) -> str:
        return FilingTextExtractor()._extract_with_regex(html)
