from typing import Any


class YahooFinanceError(Exception):
    """Raised when Yahoo Finance data cannot be fetched."""

    def __init__(
        self,
        message: str,
        *,
        ticker: str,
        period: str,
        status_code: int | None = None,
        response_body: str | None = None,
        cause: Exception | None = None,
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.ticker = ticker
        self.period = period
        self.status_code = status_code
        self.response_body = response_body
        self.cause = cause
        self.diagnostics = diagnostics or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": str(self),
            "ticker": self.ticker,
            "period": self.period,
            "status_code": self.status_code,
            "response_body": self.response_body,
            "exception_type": type(self.cause).__name__ if self.cause else None,
            "exception_message": str(self.cause) if self.cause else None,
            "diagnostics": self.diagnostics,
        }
