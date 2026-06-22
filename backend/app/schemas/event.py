from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    CEO_CHANGE = "CEO Change"
    CFO_CHANGE = "CFO Change"
    LAYOFFS = "Layoffs"
    SHARE_BUYBACK = "Share Buyback"
    SHARE_ISSUANCE = "Share Issuance"
    ACQUISITION = "Acquisition"
    DIVESTITURE = "Divestiture"
    MAJOR_CONTRACT = "Major Contract"
    CAPEX_INCREASE = "Capital Expenditure Increase"
    REGULATORY_INVESTIGATION = "Regulatory Investigation"
    PRODUCT_LAUNCH = "Product Launch"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


EVENT_TYPE_VALUES = [event_type.value for event_type in EventType]
SENTIMENT_VALUES = [sentiment.value for sentiment in Sentiment]


class ExtractedEvent(BaseModel):
    event_type: str
    summary: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    sentiment: str


class ExtractionResult(BaseModel):
    events: list[ExtractedEvent]


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filing_id: int
    event_type: str
    summary: str
    confidence: Decimal
    sentiment: str
    created_at: datetime


class EventExtractionResponse(BaseModel):
    filing_id: int
    extracted_count: int
    message: str
