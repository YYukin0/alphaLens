import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.sec_service import SECService, SECCompanyInfo, SECFilingInfo
from app.config import Settings


@pytest.fixture
def settings():
    return Settings(
        sec_user_agent="DeepEquity Test contact@test.local",
        filing_types=["8-K", "10-Q", "10-K"],
        max_filings_per_sync=10,
    )


@pytest.fixture
def sec_service(settings):
    return SECService(settings)


class TestSECService:
    def test_strip_html(self, sec_service):
        html = "<html><body><p>Hello <b>World</b></p></body></html>"
        result = sec_service.strip_html(html)
        assert "Hello" in result
        assert "World" in result
        assert "<" not in result

    @pytest.mark.asyncio
    async def test_lookup_ticker_found(self, sec_service):
        mock_data = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        }
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_data
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = await sec_service.lookup_ticker("AAPL")
            assert result is not None
            assert result.ticker == "AAPL"
            assert result.cik == "320193"
            assert result.company_name == "Apple Inc."

    @pytest.mark.asyncio
    async def test_lookup_ticker_not_found(self, sec_service):
        mock_data = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        }
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_data
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = await sec_service.lookup_ticker("INVALID")
            assert result is None



class TestCompanyRepository:
    def test_create_and_get_by_ticker(self, db_session):
        from app.models.company import Company
        from app.repositories.company_repository import CompanyRepository

        repo = CompanyRepository(db_session)
        company = Company(ticker="MSFT", company_name="Microsoft Corporation", cik="789019")
        created = repo.create(company)

        assert created.id is not None
        found = repo.get_by_ticker("MSFT")
        assert found is not None
        assert found.company_name == "Microsoft Corporation"
