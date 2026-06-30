from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AnalysisType(str, Enum):
    SUMMARY = "summary"
    RISKS = "risks"
    KPIS = "kpis"
    MDA = "mda"


ANALYSIS_TYPE_VALUES = [item.value for item in AnalysisType]


class FilingAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filing_id: int
    analysis_type: str
    content: str
    model: str | None
    created_at: datetime


class FilingAnalysisBatchResponse(BaseModel):
    filing_id: int
    analyses: list[FilingAnalysisResponse]
    message: str


class FilingAnalysisRequest(BaseModel):
    types: list[str] = Field(default_factory=lambda: ["summary", "risks", "kpis", "mda"])
    force: bool = False


class FinancialStatementTable(BaseModel):
    statement_type: str
    columns: list[str]
    rows: list[dict[str, str | None]]


class CompanyFinancialsResponse(BaseModel):
    ticker: str
    currency: str | None = None
    statements: list[FinancialStatementTable]


class CompanyProfileResponse(BaseModel):
    ticker: str
    company_name: str
    cik: str
    in_database: bool
    filing_count: int = 0
    event_count: int = 0
    latest_filing_date: str | None = None
    latest_filing_type: str | None = None
    counts_by_type: dict[str, int] = Field(default_factory=dict)
