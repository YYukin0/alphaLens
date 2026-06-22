from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.services.company_service import CompanyService
from app.services.event_service import EventService
from app.services.filing_service import FilingService
from app.services.market_data_service import MarketDataService
from app.services.openai_event_extractor import OpenAIEventExtractor
from app.services.price_service import PriceService
from app.services.sec_service import SECService


def get_sec_service(settings: Settings = Depends(get_settings)) -> SECService:
    return SECService(settings)


def get_market_data_service() -> MarketDataService:
    return MarketDataService()


def get_company_service(
    db: Session = Depends(get_db),
    sec_service: SECService = Depends(get_sec_service),
) -> CompanyService:
    return CompanyService(db, sec_service)


def get_openai_event_extractor(settings: Settings = Depends(get_settings)) -> OpenAIEventExtractor:
    return OpenAIEventExtractor(settings)


def get_event_service(
    db: Session = Depends(get_db),
    extractor: OpenAIEventExtractor = Depends(get_openai_event_extractor),
    settings: Settings = Depends(get_settings),
) -> EventService:
    return EventService(db, extractor, settings)


def get_filing_service(
    db: Session = Depends(get_db),
    sec_service: SECService = Depends(get_sec_service),
    company_service: CompanyService = Depends(get_company_service),
    settings: Settings = Depends(get_settings),
    event_service: EventService = Depends(get_event_service),
) -> FilingService:
    return FilingService(db, sec_service, company_service, settings, event_service)


def get_price_service(
    db: Session = Depends(get_db),
    market_data_service: MarketDataService = Depends(get_market_data_service),
    company_service: CompanyService = Depends(get_company_service),
) -> PriceService:
    return PriceService(db, market_data_service, company_service)
