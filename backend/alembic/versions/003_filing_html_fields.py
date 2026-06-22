"""Add raw_html and extracted_text columns to filings."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_filing_html"
down_revision: Union[str, None] = "002_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("filings", sa.Column("raw_html", sa.Text(), nullable=True))
    op.add_column("filings", sa.Column("extracted_text", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE filings
        SET extracted_text = raw_content
        WHERE extracted_text IS NULL AND raw_content IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("filings", "extracted_text")
    op.drop_column("filings", "raw_html")
