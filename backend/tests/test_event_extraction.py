from datetime import date
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.models.company import Company
from app.models.event import Event
from app.models.filing import Filing
from app.repositories.event_repository import EventRepository
from app.services.event_service import EventService
from app.services.filing_service import FilingService
from app.services.openai_event_extractor import OpenAIEventExtractor


@pytest.fixture
def settings():
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
        auto_extract_events=True,
    )


@pytest.fixture
def mock_openai_response():
    payload = {
        "events": [
            {
                "event_type": "CEO Change",
                "summary": "Company appointed a new CEO effective immediately.",
                "sentiment": "neutral",
                "confidence": 0.92,
            },
            {
                "event_type": "Share Buyback",
                "summary": "Board authorized a $1B share repurchase program.",
                "sentiment": "positive",
                "confidence": 0.88,
            },
        ]
    }

    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
    return response


class TestOpenAIEventExtractor:
    @pytest.mark.asyncio
    async def test_extract_events_parses_response(self, settings, mock_openai_response):
        extractor = OpenAIEventExtractor(settings)
        extractor._client = MagicMock()
        extractor._client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

        events = await extractor.extract_events(
            filing_content="The board appointed Jane Doe as CEO and approved a buyback.",
            filing_type="8-K",
            accession_number="0001234567-24-000001",
        )

        assert len(events) == 2
        assert events[0].event_type == "CEO Change"
        assert events[1].sentiment == "positive"


class TestEventService:
    @pytest.mark.asyncio
    async def test_extract_events_for_filing_stores_events(self, db_session, settings, mock_openai_response):
        company = Company(ticker="AAPL", company_name="Apple Inc.", cik="320193")
        db_session.add(company)
        db_session.commit()

        filing = Filing(
            company_id=company.id,
            filing_type="8-K",
            filing_date=date(2024, 1, 15),
            accession_number="0000320193-24-000002",
            sec_url="https://www.sec.gov/example",
            raw_content="CEO change and buyback announcement.",
        )
        db_session.add(filing)
        db_session.commit()

        extractor = OpenAIEventExtractor(settings)
        extractor._client = MagicMock()
        extractor._client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

        service = EventService(db_session, extractor, settings)
        count = await service.extract_events_for_filing(filing.id)

        assert count == 2
        stored = EventRepository(db_session).list_by_filing(filing.id)
        assert len(stored) == 2
        assert stored[0].confidence == Decimal("0.9200")

    @pytest.mark.asyncio
    async def test_skips_when_events_already_exist(self, db_session, settings, mock_openai_response):
        company = Company(ticker="MSFT", company_name="Microsoft", cik="789019")
        db_session.add(company)
        db_session.commit()

        filing = Filing(
            company_id=company.id,
            filing_type="8-K",
            filing_date=date(2024, 1, 15),
            accession_number="0000789019-24-000001",
            sec_url="https://www.sec.gov/example",
            raw_content="Existing content.",
        )
        db_session.add(filing)
        db_session.commit()

        db_session.add(
            Event(
                filing_id=filing.id,
                event_type="Layoffs",
                summary="Workforce reduction announced.",
                confidence=Decimal("0.80"),
                sentiment="negative",
            )
        )
        db_session.commit()

        extractor = OpenAIEventExtractor(settings)
        extractor._client = MagicMock()
        extractor._client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

        service = EventService(db_session, extractor, settings)
        count = await service.extract_events_for_filing(filing.id)

        assert count == 0
        extractor._client.chat.completions.create.assert_not_called()


class TestFilingSyncEventQueue:
    @pytest.mark.asyncio
    async def test_sync_queues_pending_extractions(self, db_session):
        from app.config import Settings
        from app.services.company_service import CompanyService
        from app.services.event_service import EventService
        from app.services.openai_event_extractor import OpenAIEventExtractor
        from app.services.sec_service import SECService

        settings = Settings(auto_extract_events=True, openai_api_key="test-key")
        company = Company(ticker="AAPL", company_name="Apple Inc.", cik="320193")
        db_session.add(company)
        db_session.commit()

        filing = Filing(
            company_id=company.id,
            filing_type="8-K",
            filing_date=date(2024, 1, 15),
            accession_number="0000320193-24-000001",
            sec_url="https://www.sec.gov/example",
            raw_content="Material event disclosure.",
            extracted_text="Material event disclosure.",
        )
        db_session.add(filing)
        db_session.commit()

        event_service = EventService(db_session, OpenAIEventExtractor(settings), settings)
        sec_service = SECService(settings)
        company_service = CompanyService(db_session, sec_service)
        filing_service = FilingService(
            db_session, sec_service, company_service, settings, event_service
        )

        with patch("app.tasks.extract_events_task.delay") as mock_delay:
            with patch.object(
                sec_service,
                "get_recent_filings",
                new_callable=AsyncMock,
                return_value=[],
            ):
                result = await filing_service.sync_filings_for_ticker("AAPL")

        assert result.synced_count == 0
        assert result.extraction_queued == 1
        mock_delay.assert_called_once_with(filing.id)
