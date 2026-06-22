from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.filing import Filing
from app.repositories.base import BaseRepository


class FilingRepository(BaseRepository[Filing]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Filing)

    def _company_filter(self, company_id: int, filing_type: str | None = None):
        stmt = select(Filing).where(Filing.company_id == company_id)
        if filing_type:
            stmt = stmt.where(Filing.filing_type == filing_type.upper())
        return stmt

    def get_by_accession_number(self, accession_number: str) -> Filing | None:
        stmt = select(Filing).where(Filing.accession_number == accession_number)
        return self.db.scalar(stmt)

    def get_by_id_with_company(self, filing_id: int) -> Filing | None:
        stmt = (
            select(Filing)
            .options(joinedload(Filing.company))
            .where(Filing.id == filing_id)
        )
        return self.db.scalar(stmt)

    def list_by_company(
        self,
        company_id: int,
        filing_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Filing]:
        stmt = self._company_filter(company_id, filing_type)
        stmt = stmt.order_by(Filing.filing_date.desc(), Filing.id.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def list_by_ticker(
        self,
        company_id: int,
        filing_types: list[str] | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Filing]:
        stmt = select(Filing).where(Filing.company_id == company_id)
        if filing_types:
            stmt = stmt.where(Filing.filing_type.in_([ft.upper() for ft in filing_types]))
        stmt = stmt.order_by(Filing.filing_date.desc(), Filing.id.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_by_company(self, company_id: int, filing_type: str | None = None) -> int:
        stmt = select(func.count()).select_from(Filing).where(Filing.company_id == company_id)
        if filing_type:
            stmt = stmt.where(Filing.filing_type == filing_type.upper())
        return int(self.db.scalar(stmt) or 0)

    def get_date_range(
        self,
        company_id: int,
        filing_type: str | None = None,
    ) -> tuple[date | None, date | None]:
        stmt = select(func.min(Filing.filing_date), func.max(Filing.filing_date)).where(
            Filing.company_id == company_id
        )
        if filing_type:
            stmt = stmt.where(Filing.filing_type == filing_type.upper())
        earliest, latest = self.db.execute(stmt).one()
        return earliest, latest

    def count_by_type(self, company_id: int) -> dict[str, int]:
        stmt = (
            select(Filing.filing_type, func.count())
            .where(Filing.company_id == company_id)
            .group_by(Filing.filing_type)
        )
        return {filing_type: count for filing_type, count in self.db.execute(stmt).all()}

    def list_missing_content(self, company_id: int, limit: int | None = None) -> list[Filing]:
        stmt = (
            select(Filing)
            .where(Filing.company_id == company_id)
            .where(Filing.extracted_text.is_(None))
            .order_by(Filing.filing_date.desc(), Filing.id.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).all())
