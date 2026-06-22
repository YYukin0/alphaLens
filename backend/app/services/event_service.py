from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.core.logging import get_logger
from app.models.event import Event
from app.models.filing import Filing
from app.repositories.event_repository import EventRepository
from app.repositories.filing_repository import FilingRepository
from app.services.openai_event_extractor import OpenAIEventExtractor

logger = get_logger(__name__)


class EventService:
    def __init__(
        self,
        db: Session,
        extractor: OpenAIEventExtractor,
        settings: Settings,
    ) -> None:
        self.db = db
        self.repo = EventRepository(db)
        self.filing_repo = FilingRepository(db)
        self.extractor = extractor
        self.settings = settings

    async def extract_events_for_filing(self, filing_id: int, force: bool = False) -> int:
        filing = self.filing_repo.get_by_id(filing_id)
        if not filing:
            raise ValueError(f"Filing {filing_id} not found")

        content = filing.extracted_text or filing.raw_content
        if not content:
            logger.warning("filing_missing_content", filing_id=filing_id)
            return 0

        if not force and self.repo.count_by_filing(filing_id) > 0:
            logger.info("events_already_extracted", filing_id=filing_id)
            return 0

        if not self.settings.openai_api_key:
            logger.warning("openai_api_key_missing", filing_id=filing_id)
            return 0

        extracted = await self.extractor.extract_events(
            filing_content=content,
            filing_type=filing.filing_type,
            accession_number=filing.accession_number,
        )

        if force:
            self.repo.delete_by_filing(filing_id)

        events = [
            Event(
                filing_id=filing_id,
                event_type=item.event_type,
                summary=item.summary,
                confidence=Decimal(str(round(item.confidence, 4))),
                sentiment=item.sentiment,
            )
            for item in extracted
        ]

        if events:
            self.repo.bulk_create(events)

        logger.info("events_stored", filing_id=filing_id, count=len(events))
        return len(events)

    def list_events_by_filing(self, filing_id: int) -> list[Event]:
        return self.repo.list_by_filing(filing_id)

    def list_events_by_ticker(self, company_id: int, skip: int = 0, limit: int = 100) -> list[Event]:
        return self.repo.list_by_company(company_id, skip, limit)

    def list_filings_pending_extraction(self, company_id: int) -> list[Filing]:
        stmt = (
            select(Filing)
            .outerjoin(Event, Event.filing_id == Filing.id)
            .where(
                Filing.company_id == company_id,
                Filing.extracted_text.isnot(None),
                Event.id.is_(None),
            )
            .order_by(Filing.filing_date.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def queue_extraction_for_filing(self, filing_id: int) -> None:
        if not self.settings.auto_extract_events:
            return
        from app.tasks import extract_events_task

        extract_events_task.delay(filing_id)
        logger.info("event_extraction_queued", filing_id=filing_id)

    def queue_pending_extractions_for_company(self, company_id: int) -> int:
        pending = self.list_filings_pending_extraction(company_id)
        for filing in pending:
            self.queue_extraction_for_filing(filing.id)
        return len(pending)
