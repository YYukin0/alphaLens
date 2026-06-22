"""Initial schema for Phase 1 MVP."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("cik", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker"),
        sa.UniqueConstraint("cik"),
    )
    op.create_index(op.f("ix_companies_id"), "companies", ["id"], unique=False)
    op.create_index(op.f("ix_companies_ticker"), "companies", ["ticker"], unique=False)
    op.create_index(op.f("ix_companies_cik"), "companies", ["cik"], unique=False)

    op.create_table(
        "filings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("filing_type", sa.String(length=16), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("accession_number", sa.String(length=32), nullable=False),
        sa.Column("sec_url", sa.String(length=512), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("accession_number", name="uq_filings_accession_number"),
    )
    op.create_index(op.f("ix_filings_id"), "filings", ["id"], unique=False)
    op.create_index(op.f("ix_filings_company_id"), "filings", ["company_id"], unique=False)
    op.create_index(op.f("ix_filings_filing_type"), "filings", ["filing_type"], unique=False)
    op.create_index(op.f("ix_filings_filing_date"), "filings", ["filing_date"], unique=False)

    op.create_table(
        "prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("high", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("low", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("close", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "date", name="uq_prices_company_date"),
    )
    op.create_index(op.f("ix_prices_id"), "prices", ["id"], unique=False)
    op.create_index(op.f("ix_prices_company_id"), "prices", ["company_id"], unique=False)
    op.create_index(op.f("ix_prices_date"), "prices", ["date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_prices_date"), table_name="prices")
    op.drop_index(op.f("ix_prices_company_id"), table_name="prices")
    op.drop_index(op.f("ix_prices_id"), table_name="prices")
    op.drop_table("prices")

    op.drop_index(op.f("ix_filings_filing_date"), table_name="filings")
    op.drop_index(op.f("ix_filings_filing_type"), table_name="filings")
    op.drop_index(op.f("ix_filings_company_id"), table_name="filings")
    op.drop_index(op.f("ix_filings_id"), table_name="filings")
    op.drop_table("filings")

    op.drop_index(op.f("ix_companies_cik"), table_name="companies")
    op.drop_index(op.f("ix_companies_ticker"), table_name="companies")
    op.drop_index(op.f("ix_companies_id"), table_name="companies")
    op.drop_table("companies")
