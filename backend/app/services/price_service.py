from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.price import Price
from app.repositories.price_repository import PriceRepository
from app.services.company_service import CompanyService
from app.services.market_data_service import MarketDataService


class PriceService:
    def __init__(
        self,
        db: Session,
        market_data_service: MarketDataService,
        company_service: CompanyService,
    ) -> None:
        self.repo = PriceRepository(db)
        self.market_data_service = market_data_service
        self.company_service = company_service

    async def sync_prices_for_ticker(self, ticker: str, period: str = "1y") -> int:
        company = await self.company_service.get_or_create_company(ticker)
        records = await self.market_data_service.fetch_historical_prices(ticker, period)

        prices = [
            Price(
                company_id=company.id,
                date=record.date,
                open=record.open,
                high=record.high,
                low=record.low,
                close=record.close,
                volume=record.volume,
            )
            for record in records
        ]

        return self.repo.bulk_upsert(prices)

    def list_prices_by_ticker(self, ticker: str, limit: int = 500) -> list[Price]:
        company = self.company_service.get_company_by_ticker(ticker)
        if not company:
            return []
        return self.repo.list_by_company(company.id, limit=limit)
