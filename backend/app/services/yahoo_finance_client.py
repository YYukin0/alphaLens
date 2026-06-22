import json
import traceback
from typing import Any

import httpx
import pandas as pd

from app.core.logging import get_logger
from app.exceptions.yahoo_finance import YahooFinanceError

logger = get_logger(__name__)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


class YahooFinanceClient:
    """Fetch and parse Yahoo Finance chart API responses directly."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
    }

    def probe_chart_api(self, ticker: str, period: str) -> dict[str, Any]:
        url = YAHOO_CHART_URL.format(ticker=ticker.upper())
        params = {"range": period, "interval": "1d"}

        logger.info("yahoo_http_probe_start", ticker=ticker, period=period, url=url, params=params)

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True, headers=self.DEFAULT_HEADERS) as client:
                response = client.get(url, params=params)
                body = response.text

                logger.info(
                    "yahoo_http_probe_complete",
                    ticker=ticker,
                    period=period,
                    status_code=response.status_code,
                    response_body_preview=body[:1000],
                )

                parsed_json: Any | None
                try:
                    parsed_json = response.json()
                except json.JSONDecodeError:
                    parsed_json = None

                return {
                    "url": str(response.url),
                    "status_code": response.status_code,
                    "response_body": body,
                    "response_json": parsed_json,
                    "response_headers": dict(response.headers),
                }
        except Exception as exc:
            logger.error(
                "yahoo_http_probe_failed",
                ticker=ticker,
                period=period,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                exc_info=True,
            )
            raise

    @staticmethod
    def parse_chart_json(chart_json: dict[str, Any]) -> pd.DataFrame:
        """Parse Yahoo v8 chart JSON into an OHLCV DataFrame."""
        chart = chart_json.get("chart")
        if not isinstance(chart, dict):
            raise TypeError(f"Expected chart object in Yahoo response, got {type(chart).__name__}")

        error = chart.get("error")
        if error:
            raise ValueError(f"Yahoo chart API returned error: {error}")

        results = chart.get("result")
        if not results:
            return pd.DataFrame()

        result = results[0]
        timestamps = result.get("timestamp") or []
        quotes = result.get("indicators", {}).get("quote") or []
        if not timestamps or not quotes:
            return pd.DataFrame()

        quote = quotes[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        rows: list[dict[str, Any]] = []
        row_timestamps: list[int] = []
        for index, timestamp in enumerate(timestamps):
            close = closes[index] if index < len(closes) else None
            if close is None:
                continue

            row_timestamps.append(timestamp)
            rows.append(
                {
                    "Open": opens[index] if index < len(opens) else close,
                    "High": highs[index] if index < len(highs) else close,
                    "Low": lows[index] if index < len(lows) else close,
                    "Close": close,
                    "Volume": volumes[index] if index < len(volumes) else 0,
                }
            )

        if not rows:
            return pd.DataFrame()

        index = pd.to_datetime(row_timestamps, unit="s", utc=True).tz_localize(None)
        return pd.DataFrame(rows, index=index)

    def fetch_history_dataframe(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        ticker = ticker.upper().strip()

        logger.info("yahoo_history_fetch_start", ticker=ticker, period=period)

        probe = self.probe_chart_api(ticker, period)

        if probe["status_code"] != 200:
            message = f"Yahoo chart API returned HTTP {probe['status_code']} for '{ticker}'"
            logger.error(
                "yahoo_history_http_error",
                ticker=ticker,
                period=period,
                status_code=probe["status_code"],
                response_body_preview=probe.get("response_body", "")[:1000],
            )
            raise YahooFinanceError(
                message,
                ticker=ticker,
                period=period,
                status_code=probe["status_code"],
                response_body=probe.get("response_body"),
                diagnostics={"http_probe": probe},
            )

        chart_json = probe.get("response_json")
        if chart_json is None:
            try:
                chart_json = json.loads(probe["response_body"])
            except json.JSONDecodeError as exc:
                logger.error(
                    "yahoo_history_json_decode_failed",
                    ticker=ticker,
                    period=period,
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                    response_body_preview=probe.get("response_body", "")[:1000],
                    exc_info=True,
                )
                raise

        try:
            history = self.parse_chart_json(chart_json)
        except Exception as exc:
            logger.error(
                "yahoo_history_parse_failed",
                ticker=ticker,
                period=period,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                status_code=probe["status_code"],
                response_body_preview=probe.get("response_body", "")[:1000],
                exc_info=True,
            )
            raise

        if history.empty:
            message = f"No price data returned for '{ticker}' (period={period})"
            logger.error(
                "yahoo_history_empty",
                ticker=ticker,
                period=period,
                status_code=probe["status_code"],
                response_body_preview=probe.get("response_body", "")[:1000],
            )
            raise YahooFinanceError(
                message,
                ticker=ticker,
                period=period,
                status_code=probe["status_code"],
                response_body=probe.get("response_body"),
                diagnostics={"http_probe": probe},
            )

        logger.info("yahoo_history_fetch_success", ticker=ticker, period=period, rows=len(history))
        return history

    def _capture_step(self, step_name: str, func) -> dict[str, Any]:
        try:
            result = func()
            return {"step": step_name, "success": True, "result": result}
        except Exception as exc:
            logger.error(
                "yahoo_debug_step_failed",
                step=step_name,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                exc_info=True,
            )
            return {
                "step": step_name,
                "success": False,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc(),
            }

    def fetch_debug_snapshot(self, ticker: str, period: str = "1y") -> dict[str, Any]:
        ticker = ticker.upper().strip()
        snapshot: dict[str, Any] = {
            "ticker": ticker,
            "period": period,
            "parser": "yahoo_chart_json",
            "steps": [],
        }

        snapshot["steps"].append(
            self._capture_step("http_probe", lambda: self.probe_chart_api(ticker, period))
        )

        def fetch_history_step() -> dict[str, Any]:
            probe = self.probe_chart_api(ticker, period)
            chart_json = probe.get("response_json")
            if chart_json is None:
                chart_json = json.loads(probe["response_body"])
            history = self.parse_chart_json(chart_json)
            payload = {
                "empty": history.empty,
                "rows": len(history),
                "columns": list(history.columns),
            }
            if not history.empty:
                payload["head"] = json.loads(history.head(5).to_json(orient="split"))
                payload["tail"] = json.loads(history.tail(5).to_json(orient="split"))
            return payload

        snapshot["steps"].append(self._capture_step("history", fetch_history_step))

        return snapshot
