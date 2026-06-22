import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.exceptions.yahoo_finance import YahooFinanceError
from app.services.market_data_service import MarketDataService
from app.services.yahoo_finance_client import YahooFinanceClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def aapl_chart_json() -> dict:
    return json.loads((FIXTURES_DIR / "aapl_chart.json").read_text())


class TestYahooChartParser:
    def test_parse_aapl_chart_json_success(self, aapl_chart_json):
        history = YahooFinanceClient.parse_chart_json(aapl_chart_json)

        assert not history.empty
        assert list(history.columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert len(history) == 3
        assert history.iloc[0]["Close"] == pytest.approx(193.2)
        assert history.iloc[1]["Volume"] == 48230000

    def test_parse_chart_json_skips_null_closes(self, aapl_chart_json):
        history = YahooFinanceClient.parse_chart_json(aapl_chart_json)
        assert all(history["Close"].notna())

    def test_parse_invalid_chart_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected chart object"):
            YahooFinanceClient.parse_chart_json({"chart": "invalid"})

    def test_parse_chart_api_error_raises_value_error(self):
        payload = {"chart": {"result": [], "error": {"code": "Not Found", "description": "No data"}}}
        with pytest.raises(ValueError, match="Yahoo chart API returned error"):
            YahooFinanceClient.parse_chart_json(payload)


class TestYahooFinanceClient:
    def test_fetch_history_dataframe_parses_aapl_response(self, aapl_chart_json):
        client = YahooFinanceClient()
        probe = {
            "url": "https://query1.finance.yahoo.com/v8/finance/chart/AAPL",
            "status_code": 200,
            "response_body": json.dumps(aapl_chart_json),
            "response_json": aapl_chart_json,
            "response_headers": {"content-type": "application/json"},
        }

        with patch.object(client, "probe_chart_api", return_value=probe):
            history = client.fetch_history_dataframe("AAPL", "1y")

        assert len(history) == 3
        assert history.iloc[-1]["Close"] == pytest.approx(194.5)

    def test_fetch_history_dataframe_reraises_parser_exception(self, aapl_chart_json):
        client = YahooFinanceClient()
        probe = {
            "status_code": 200,
            "response_body": json.dumps(aapl_chart_json),
            "response_json": aapl_chart_json,
        }

        with patch.object(client, "probe_chart_api", return_value=probe):
            with patch.object(client, "parse_chart_json", side_effect=TypeError("bad chart shape")):
                with pytest.raises(TypeError, match="bad chart shape"):
                    client.fetch_history_dataframe("AAPL", "1y")

    def test_fetch_history_dataframe_raises_when_empty_result(self):
        client = YahooFinanceClient()
        empty_payload = {"chart": {"result": [], "error": None}}
        probe = {
            "status_code": 200,
            "response_body": json.dumps(empty_payload),
            "response_json": empty_payload,
        }

        with patch.object(client, "probe_chart_api", return_value=probe):
            with pytest.raises(YahooFinanceError, match="No price data returned"):
                client.fetch_history_dataframe("AAPL", "1y")

    def test_probe_chart_api_returns_status_and_body(self):
        client = YahooFinanceClient()
        mock_response = MagicMock()
        mock_response.url = "https://query1.finance.yahoo.com/v8/finance/chart/AAPL"
        mock_response.status_code = 200
        mock_response.text = '{"chart":{"result":[]}}'
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"chart": {"result": []}}

        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = False
        mock_http_client.get.return_value = mock_response

        with patch("httpx.Client", return_value=mock_http_client):
            result = client.probe_chart_api("AAPL", "1y")

        assert result["status_code"] == 200
        assert "chart" in result["response_body"]


class TestMarketDataService:
    @pytest.mark.asyncio
    async def test_fetch_historical_prices_aapl_success(self, aapl_chart_json):
        service = MarketDataService()
        history = YahooFinanceClient.parse_chart_json(aapl_chart_json)

        with patch.object(service.client, "fetch_history_dataframe", return_value=history):
            records = await service.fetch_historical_prices("AAPL")

        assert len(records) == 3
        assert records[0].date == date(2024, 1, 2)
        assert records[0].close == Decimal("193.2000")
        assert records[1].volume == 48230000

    @pytest.mark.asyncio
    async def test_fetch_historical_prices_raises_on_empty_history(self):
        service = MarketDataService()
        with patch.object(
            service.client,
            "fetch_history_dataframe",
            side_effect=YahooFinanceError(
                "No price data returned for 'GOOG' (period=1y)",
                ticker="GOOG",
                period="1y",
                status_code=200,
                response_body='{"chart":{"result":[]}}',
            ),
        ):
            with pytest.raises(YahooFinanceError):
                await service.fetch_historical_prices("GOOG")
