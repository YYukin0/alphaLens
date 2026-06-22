from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Company)

    def get_by_ticker(self, ticker: str) -> Company | None:
        stmt = select(Company).where(Company.ticker == ticker.upper())
        return self.db.scalar(stmt)

    def get_by_cik(self, cik: str) -> Company | None:
        normalized_cik = cik.lstrip("0") or "0"
        stmt = select(Company).where(Company.cik == normalized_cik)
        return self.db.scalar(stmt)

    def list_all(self, skip: int = 0, limit: int = 100) -> list[Company]:
        stmt = select(Company).order_by(Company.ticker).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def search_by_ticker_prefix(self, query: str, limit: int = 20) -> list[Company]:
        stmt = (
            select(Company)
            .where(Company.ticker.ilike(f"{query.upper()}%"))
            .order_by(Company.ticker)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
