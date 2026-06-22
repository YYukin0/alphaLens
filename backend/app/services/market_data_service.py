from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd

from app.core.logging import get_logger
from app.services.yahoo_finance_client import YahooFinanceClient

logger = get_logger(__name__)


@dataclass
class MarketPriceRecord:
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class MarketDataService:
    """Fetch market data from Yahoo Finance."""

    def __init__(self, client: YahooFinanceClient | None = None) -> None:
        self.client = client or YahooFinanceClient()

    async def fetch_historical_prices(self, ticker: str, period: str = "1y") -> list[MarketPriceRecord]:
        ticker = ticker.upper().strip()
        history = self.client.fetch_history_dataframe(ticker, period)
        records = self._dataframe_to_records(history)
        logger.info("market_data_fetched", ticker=ticker, period=period, count=len(records))
        return records

    def fetch_debug_snapshot(self, ticker: str, period: str = "1y") -> dict:
        return self.client.fetch_debug_snapshot(ticker, period)

    @staticmethod
    def _dataframe_to_records(history: pd.DataFrame) -> list[MarketPriceRecord]:
        records: list[MarketPriceRecord] = []
        for idx, row in history.iterrows():
            record_date = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
            records.append(
                MarketPriceRecord(
                    date=record_date,
                    open=Decimal(str(round(row["Open"], 4))),
                    high=Decimal(str(round(row["High"], 4))),
                    low=Decimal(str(round(row["Low"], 4))),
                    close=Decimal(str(round(row["Close"], 4))),
                    volume=int(row["Volume"]),
                )
            )
        return records
