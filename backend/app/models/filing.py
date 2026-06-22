from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Filing(Base):
    __tablename__ = "filings"
    __table_args__ = (UniqueConstraint("accession_number", name="uq_filings_accession_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    filing_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    accession_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    sec_url: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sections_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="filings")
    events: Mapped[list["Event"]] = relationship(back_populates="filing", cascade="all, delete-orphan")
