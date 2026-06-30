"""Add filing AI analyses table."""

from alembic import op
import sqlalchemy as sa

revision = "005_filing_analyses"
down_revision = "004_filing_sections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "filing_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filing_id", sa.Integer(), sa.ForeignKey("filings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("filing_id", "analysis_type", name="uq_filing_analysis_type"),
    )
    op.create_index("ix_filing_analyses_filing_id", "filing_analyses", ["filing_id"])
    op.create_index("ix_filing_analyses_analysis_type", "filing_analyses", ["analysis_type"])


def downgrade() -> None:
    op.drop_index("ix_filing_analyses_analysis_type", table_name="filing_analyses")
    op.drop_index("ix_filing_analyses_filing_id", table_name="filing_analyses")
    op.drop_table("filing_analyses")
