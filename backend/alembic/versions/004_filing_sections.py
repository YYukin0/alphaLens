"""Add parsed filing sections JSON column."""

from alembic import op
import sqlalchemy as sa

revision = "004_filing_sections"
down_revision = "003_filing_html"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("filings", sa.Column("sections_data", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("filings", "sections_data")
