import asyncio

from app.celery_app import celery_app
from app.core.logging import get_logger, setup_logging
from app.database import SessionLocal
from app.services.market_data_service import MarketDataService
from app.services.sec_service import SECService
from app.config import get_settings
from app.services.company_service import CompanyService
from app.services.event_service import EventService
from app.services.filing_service import FilingService
from app.services.openai_event_extractor import OpenAIEventExtractor
from app.services.price_service import PriceService

logger = get_logger(__name__)
setup_logging()


def _run_async(coro):
    return asyncio.run(coro)


def _build_event_service(db):
    settings = get_settings()
    extractor = OpenAIEventExtractor(settings)
    return EventService(db, extractor, settings)


def _build_filing_service(db):
    settings = get_settings()
    sec_service = SECService(settings)
    company_service = CompanyService(db, sec_service)
    event_service = _build_event_service(db)
    return FilingService(db, sec_service, company_service, settings, event_service)


@celery_app.task(name="app.tasks.sync_filings_task", bind=True, max_retries=3)
def sync_filings_task(self, ticker: str, limit: int = 10) -> dict:
    db = SessionLocal()
    try:
        filing_service = _build_filing_service(db)
        result = _run_async(filing_service.sync_filings_for_ticker(ticker, limit))
        logger.info(
            "celery_filings_synced",
            ticker=ticker,
            synced=result.synced_count,
            extraction_queued=result.extraction_queued,
        )
        return {
            "ticker": ticker.upper(),
            "synced_count": result.synced_count,
            "extraction_queued": result.extraction_queued,
        }
    except Exception as exc:
        logger.error("celery_filings_failed", ticker=ticker, error=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        db.close()


@celery_app.task(name="app.tasks.sync_historical_filing_content_task", bind=True, max_retries=3)
def sync_historical_filing_content_task(self, ticker: str, batch_size: int = 25) -> dict:
    db = SessionLocal()
    try:
        filing_service = _build_filing_service(db)
        total_synced = 0
        total_queued = 0

        while True:
            result = _run_async(
                filing_service.sync_pending_filing_content_for_ticker(ticker, limit=batch_size)
            )
            total_synced += result.synced_count
            total_queued += result.extraction_queued
            if result.synced_count < batch_size:
                break

        logger.info(
            "celery_historical_content_synced",
            ticker=ticker,
            synced=total_synced,
            extraction_queued=total_queued,
        )
        return {
            "ticker": ticker.upper(),
            "synced_count": total_synced,
            "extraction_queued": total_queued,
        }
    except Exception as exc:
        logger.error("celery_historical_content_failed", ticker=ticker, error=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        db.close()


@celery_app.task(name="app.tasks.extract_events_task", bind=True, max_retries=3)
def extract_events_task(self, filing_id: int, force: bool = False) -> dict:
    db = SessionLocal()
    try:
        event_service = _build_event_service(db)
        count = _run_async(event_service.extract_events_for_filing(filing_id, force=force))
        logger.info("celery_events_extracted", filing_id=filing_id, count=count)
        return {"filing_id": filing_id, "extracted_count": count}
    except Exception as exc:
        logger.error("celery_events_failed", filing_id=filing_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        db.close()


@celery_app.task(name="app.tasks.sync_prices_task", bind=True, max_retries=3)
def sync_prices_task(self, ticker: str, period: str = "1y") -> dict:
    db = SessionLocal()
    try:
        settings = get_settings()
        sec_service = SECService(settings)
        company_service = CompanyService(db, sec_service)
        market_data_service = MarketDataService()
        price_service = PriceService(db, market_data_service, company_service)
        count = _run_async(price_service.sync_prices_for_ticker(ticker, period))
        logger.info("celery_prices_synced", ticker=ticker, count=count)
        return {"ticker": ticker.upper(), "synced_count": count}
    except Exception as exc:
        logger.error("celery_prices_failed", ticker=ticker, error=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        db.close()
