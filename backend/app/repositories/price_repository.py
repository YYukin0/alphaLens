from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.price import Price
from app.repositories.base import BaseRepository


class PriceRepository(BaseRepository[Price]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Price)

    def list_by_company(
        self,
        company_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 500,
    ) -> list[Price]:
        stmt = select(Price).where(Price.company_id == company_id)
        if start_date:
            stmt = stmt.where(Price.date >= start_date)
        if end_date:
            stmt = stmt.where(Price.date <= end_date)
        stmt = stmt.order_by(Price.date.asc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def bulk_upsert(self, prices: list[Price]) -> int:
        if not prices:
            return 0

        values = [
            {
                "company_id": price.company_id,
                "date": price.date,
                "open": price.open,
                "high": price.high,
                "low": price.low,
                "close": price.close,
                "volume": price.volume,
            }
            for price in prices
        ]

        stmt = insert(Price).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_prices_company_date",
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
            },
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount or len(values)
