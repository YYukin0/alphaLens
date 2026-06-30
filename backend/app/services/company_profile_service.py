from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.filing import Filing
from app.repositories.company_repository import CompanyRepository
from app.repositories.filing_repository import FilingRepository
from app.schemas.analysis import CompanyProfileResponse
from app.services.company_service import CompanyService


class CompanyProfileService:
    def __init__(self, db: Session, company_service: CompanyService) -> None:
        self.db = db
        self.company_service = company_service
        self.company_repo = CompanyRepository(db)
        self.filing_repo = FilingRepository(db)

    async def get_profile(self, ticker: str) -> CompanyProfileResponse:
        ticker = ticker.upper().strip()
        company = self.company_service.get_company_by_ticker(ticker)

        if company:
            return self._profile_from_db(company)

        search = await self.company_service.search_ticker(ticker)
        return CompanyProfileResponse(
            ticker=search.ticker,
            company_name=search.company_name,
            cik=search.cik,
            in_database=False,
        )

    def _profile_from_db(self, company) -> CompanyProfileResponse:
        filing_stats = (
            self.db.query(Filing.filing_type, func.count(Filing.id))
            .filter(Filing.company_id == company.id)
            .group_by(Filing.filing_type)
            .all()
        )
        counts_by_type = {ftype: count for ftype, count in filing_stats}
        filing_count = sum(counts_by_type.values())

        latest = (
            self.db.query(Filing)
            .filter(Filing.company_id == company.id)
            .order_by(Filing.filing_date.desc(), Filing.id.desc())
            .first()
        )

        event_count = (
            self.db.query(func.count(Event.id))
            .join(Filing, Event.filing_id == Filing.id)
            .filter(Filing.company_id == company.id)
            .scalar()
            or 0
        )

        return CompanyProfileResponse(
            ticker=company.ticker,
            company_name=company.company_name,
            cik=company.cik,
            in_database=True,
            filing_count=filing_count,
            event_count=event_count,
            latest_filing_date=latest.filing_date.isoformat() if latest else None,
            latest_filing_type=latest.filing_type if latest else None,
            counts_by_type=counts_by_type,
        )
