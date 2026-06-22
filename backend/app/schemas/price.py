from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PriceBase(BaseModel):
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class PriceResponse(PriceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    created_at: datetime


class PriceSyncRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16, examples=["AAPL"])
    period: str = Field(default="1y", pattern=r"^(1mo|3mo|6mo|1y|2y|5y|max)$")


class PriceSyncResponse(BaseModel):
    ticker: str
    synced_count: int
    message: str
