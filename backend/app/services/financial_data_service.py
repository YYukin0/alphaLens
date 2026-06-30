import yfinance as yf

from app.core.logging import get_logger
from app.schemas.analysis import CompanyFinancialsResponse, FinancialStatementTable

logger = get_logger(__name__)

STATEMENT_MAP = {
    "income_statement": "financials",
    "balance_sheet": "balance_sheet",
    "cash_flow": "cashflow",
}


class FinancialDataService:
    """Fetch financial statements from Yahoo Finance."""

    def fetch_financials(self, ticker: str) -> CompanyFinancialsResponse:
        ticker = ticker.upper().strip()
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        currency = info.get("currency")

        statements: list[FinancialStatementTable] = []
        for statement_type, attr in STATEMENT_MAP.items():
            frame = getattr(stock, attr, None)
            if frame is None or frame.empty:
                continue
            statements.append(self._frame_to_table(statement_type, frame))

        if not statements:
            logger.warning("financials_empty", ticker=ticker)

        return CompanyFinancialsResponse(ticker=ticker, currency=currency, statements=statements)

    @staticmethod
    def _frame_to_table(statement_type: str, frame) -> FinancialStatementTable:
        columns = [col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col) for col in frame.columns]
        rows: list[dict[str, str | None]] = []
        for index, row in frame.iterrows():
            label = str(index)
            values: dict[str, str | None] = {"line_item": label}
            for col_name, value in row.items():
                key = col_name.strftime("%Y-%m-%d") if hasattr(col_name, "strftime") else str(col_name)
                if value is None or (isinstance(value, float) and value != value):
                    values[key] = None
                else:
                    values[key] = f"{float(value):,.0f}" if abs(float(value)) >= 1 else f"{float(value):,.4f}"
            rows.append(values)
        return FinancialStatementTable(
            statement_type=statement_type,
            columns=["line_item", *columns],
            rows=rows[:40],
        )

    def fetch_key_metrics(self, ticker: str) -> dict[str, str | float | None]:
        ticker = ticker.upper().strip()
        info = yf.Ticker(ticker).info or {}
        keys = [
            "marketCap",
            "trailingPE",
            "forwardPE",
            "priceToBook",
            "profitMargins",
            "operatingMargins",
            "returnOnEquity",
            "revenueGrowth",
            "earningsGrowth",
            "totalRevenue",
            "ebitda",
            "sharesOutstanding",
            "52WeekHigh",
            "52WeekLow",
        ]
        return {key: info.get(key) for key in keys if info.get(key) is not None}
