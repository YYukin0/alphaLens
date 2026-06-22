from sqlalchemy.orm import Session

from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.schemas.company import CompanySearchResponse
from app.services.sec_service import SECService


class CompanyService:
    def __init__(self, db: Session, sec_service: SECService) -> None:
        self.repo = CompanyRepository(db)
        self.sec_service = sec_service

    async def search_ticker(self, ticker: str) -> CompanySearchResponse:
        ticker = ticker.upper().strip()
        existing = self.repo.get_by_ticker(ticker)

        if existing:
            return CompanySearchResponse(
                ticker=existing.ticker,
                company_name=existing.company_name,
                cik=existing.cik,
                in_database=True,
            )

        sec_info = await self.sec_service.lookup_ticker(ticker)
        if not sec_info:
            raise ValueError(f"Ticker '{ticker}' not found in SEC EDGAR")

        return CompanySearchResponse(
            ticker=sec_info.ticker,
            company_name=sec_info.company_name,
            cik=sec_info.cik,
            in_database=False,
        )

    async def get_or_create_company(self, ticker: str) -> Company:
        ticker = ticker.upper().strip()
        existing = self.repo.get_by_ticker(ticker)
        if existing:
            return existing

        sec_info = await self.sec_service.lookup_ticker(ticker)
        if not sec_info:
            raise ValueError(f"Ticker '{ticker}' not found in SEC EDGAR")

        company = Company(
            ticker=sec_info.ticker,
            company_name=sec_info.company_name,
            cik=sec_info.cik,
        )
        return self.repo.create(company)

    def get_company_by_ticker(self, ticker: str) -> Company | None:
        return self.repo.get_by_ticker(ticker.upper().strip())

    def list_companies(self, skip: int = 0, limit: int = 100) -> list[Company]:
        return self.repo.list_all(skip=skip, limit=limit)

    def search_local(self, query: str, limit: int = 20) -> list[Company]:
        return self.repo.search_by_ticker_prefix(query, limit=limit)
