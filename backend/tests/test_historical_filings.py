import json
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.models.company import Company
from app.models.filing import Filing
from app.repositories.company_repository import CompanyRepository
from app.repositories.filing_repository import FilingRepository
from app.services.company_service import CompanyService
from app.services.filing_service import FilingService
from app.services.sec_service import SECService

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings():
    return Settings(
        sec_user_agent="AlphaLens Test contact@test.local",
        filing_types=["8-K", "10-Q", "10-K"],
        max_filings_per_sync=10,
        historical_filing_years=10,
        default_filing_page_size=25,
    )


@pytest.fixture
def sec_service(settings):
    return SECService(settings)


@pytest.fixture
def goog_submissions():
    return json.loads((FIXTURES_DIR / "goog_submissions.json").read_text())


@pytest.fixture
def goog_archive():
    return json.loads((FIXTURES_DIR / "goog_submissions_archive.json").read_text())


class TestHistoricalSECService:
    @pytest.mark.asyncio
    async def test_get_historical_filings_merges_recent_and_archive(
        self, sec_service, goog_submissions, goog_archive
    ):
        with patch.object(sec_service, "fetch_submissions", new_callable=AsyncMock) as mock_main, patch.object(
            sec_service, "fetch_submissions_file", new_callable=AsyncMock
        ) as mock_archive:
            mock_main.return_value = goog_submissions
            mock_archive.return_value = goog_archive

            filings = await sec_service.get_historical_filings("1652044")

        accession_numbers = {filing.accession_number for filing in filings}
        assert len(filings) == len(accession_numbers)
        assert all(filing.filing_type in {"8-K", "10-Q", "10-K"} for filing in filings)

        counts = {}
        for filing in filings:
            counts[filing.filing_type] = counts.get(filing.filing_type, 0) + 1

        assert counts["10-K"] >= 10
        assert counts["10-Q"] >= 30
        assert counts["8-K"] >= 100
        assert min(filing.filing_date for filing in filings) >= date(2016, 1, 1)

    @pytest.mark.asyncio
    async def test_get_historical_filings_deduplicates_accessions(
        self, sec_service, goog_submissions, goog_archive
    ):
        overlap_accession = goog_submissions["filings"]["recent"]["accessionNumber"][0]
        goog_archive["accessionNumber"].insert(0, overlap_accession)
        goog_archive["form"].insert(0, goog_submissions["filings"]["recent"]["form"][0])
        goog_archive["filingDate"].insert(0, goog_submissions["filings"]["recent"]["filingDate"][0])
        goog_archive["primaryDocument"].insert(
            0, goog_submissions["filings"]["recent"]["primaryDocument"][0]
        )

        with patch.object(sec_service, "fetch_submissions", new_callable=AsyncMock) as mock_main, patch.object(
            sec_service, "fetch_submissions_file", new_callable=AsyncMock
        ) as mock_archive:
            mock_main.return_value = goog_submissions
            mock_archive.return_value = goog_archive

            filings = await sec_service.get_historical_filings("1652044")

        assert len(filings) == len({filing.accession_number for filing in filings})


class TestHistoricalFilingService:
    @pytest.mark.asyncio
    async def test_sync_historical_filings_indexes_metadata(self, db_session, settings, goog_submissions, goog_archive):
        sec_service = SECService(settings)
        company_repo = CompanyRepository(db_session)
        company = company_repo.create(
            Company(ticker="GOOG", company_name="Alphabet Inc.", cik="1652044")
        )
        company_service = CompanyService(db_session, sec_service)
        filing_service = FilingService(db_session, sec_service, company_service, settings)

        sample_filings = sec_service._parse_filing_batch(
            goog_submissions["filings"]["recent"], "1652044", settings.filing_types
        )
        sample_filings.extend(
            sec_service._parse_filing_batch(goog_archive, "1652044", settings.filing_types)
        )
        deduped = list({filing.accession_number: filing for filing in sample_filings}.values())

        with patch.object(
            sec_service,
            "get_historical_filings",
            new_callable=AsyncMock,
            return_value=deduped,
        ):
            result = await filing_service.sync_historical_filings_for_ticker("GOOG", download_content=False)

        repo = FilingRepository(db_session)
        assert result.discovered_count == len(deduped)
        assert result.total_count == repo.count_by_company(company.id)
        assert result.counts_by_type["10-K"] >= 10
        assert result.counts_by_type["10-Q"] >= 30
        assert result.counts_by_type["8-K"] >= 100
        assert result.earliest_filing_date is not None
        assert result.latest_filing_date is not None

    def test_list_filings_by_ticker_is_paginated(self, db_session, settings):
        sec_service = SECService(settings)
        company_repo = CompanyRepository(db_session)
        company = company_repo.create(
            Company(ticker="GOOG", company_name="Alphabet Inc.", cik="1652044")
        )
        filing_repo = FilingRepository(db_session)
        for idx in range(30):
            filing_repo.create(
                Filing(
                    company_id=company.id,
                    filing_type="8-K",
                    filing_date=date(2024, 1, min(idx + 1, 28)),
                    accession_number=f"0001193125-24-{idx:06d}",
                    sec_url=f"https://example.com/{idx}",
                )
            )

        company_service = CompanyService(db_session, sec_service)
        filing_service = FilingService(db_session, sec_service, company_service, settings)

        page_one = filing_service.list_filings_by_ticker("GOOG", page=1, page_size=25)
        page_two = filing_service.list_filings_by_ticker("GOOG", page=2, page_size=25)

        assert page_one is not None
        assert len(page_one.items) == 25
        assert page_one.total_count == 30
        assert page_one.total_pages == 2
        assert page_one.stats.total_count == 30
        assert len(page_two.items) == 5


class TestHistoricalFilingsAPI:
    def test_list_filings_returns_pagination(self, client, db_session, settings):
        sec_service = SECService(settings)
        company_repo = CompanyRepository(db_session)
        company = company_repo.create(
            Company(ticker="GOOG", company_name="Alphabet Inc.", cik="1652044")
        )
        filing_repo = FilingRepository(db_session)
        filing_repo.create(
            Filing(
                company_id=company.id,
                filing_type="10-K",
                filing_date=date(2024, 1, 1),
                accession_number="0001193125-24-000001",
                sec_url="https://example.com/1",
            )
        )

        response = client.get("/api/v1/filings/GOOG?page=1&page_size=25")
        assert response.status_code == 200
        payload = response.json()
        assert payload["page"] == 1
        assert payload["page_size"] == 25
        assert payload["total_count"] == 1
        assert payload["total_pages"] == 1
        assert payload["stats"]["total_count"] == 1
        assert len(payload["items"]) == 1

    def test_sync_historical_filings_endpoint(self, client, db_session, settings, goog_submissions, goog_archive):
        sec_service = SECService(settings)
        company_repo = CompanyRepository(db_session)
        company_repo.create(Company(ticker="GOOG", company_name="Alphabet Inc.", cik="1652044"))
        deduped = list(
            {
                filing.accession_number: filing
                for filing in (
                    sec_service._parse_filing_batch(
                        goog_submissions["filings"]["recent"], "1652044", settings.filing_types
                    )
                    + sec_service._parse_filing_batch(goog_archive, "1652044", settings.filing_types)
                )
            }.values()
        )

        with patch(
            "app.services.sec_service.SECService.get_historical_filings",
            new_callable=AsyncMock,
            return_value=deduped,
        ), patch("app.tasks.sync_historical_filing_content_task.delay") as mock_delay:
            response = client.post(
                "/api/v1/filings/sync/historical",
                json={"ticker": "GOOG", "years": 10},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["discovered_count"] == len(deduped)
        assert payload["total_count"] == len(deduped)
        assert payload["counts_by_type"]["10-K"] >= 10
        assert payload["counts_by_type"]["10-Q"] >= 30
        assert payload["counts_by_type"]["8-K"] >= 100
        mock_delay.assert_called_once_with("GOOG")
