from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16, examples=["AAPL"])
    company_name: str = Field(..., min_length=1, max_length=255)
    cik: str = Field(..., min_length=1, max_length=20)


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class CompanySearchResponse(BaseModel):
    ticker: str
    company_name: str
    cik: str
    in_database: bool = False
