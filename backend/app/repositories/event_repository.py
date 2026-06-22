from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Event)

    def list_by_filing(self, filing_id: int) -> list[Event]:
        stmt = select(Event).where(Event.filing_id == filing_id).order_by(Event.confidence.desc())
        return list(self.db.scalars(stmt).all())

    def list_by_company(self, company_id: int, skip: int = 0, limit: int = 100) -> list[Event]:
        from app.models.filing import Filing

        stmt = (
            select(Event)
            .join(Filing, Event.filing_id == Filing.id)
            .where(Filing.company_id == company_id)
            .order_by(Filing.filing_date.desc(), Event.confidence.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def count_by_filing(self, filing_id: int) -> int:
        stmt = select(Event).where(Event.filing_id == filing_id)
        return len(list(self.db.scalars(stmt).all()))

    def delete_by_filing(self, filing_id: int) -> int:
        events = self.list_by_filing(filing_id)
        for event in events:
            self.db.delete(event)
        self.db.commit()
        return len(events)

    def bulk_create(self, events: list[Event]) -> list[Event]:
        self.db.add_all(events)
        self.db.commit()
        for event in events:
            self.db.refresh(event)
        return events
