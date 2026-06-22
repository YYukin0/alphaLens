from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_debug_yahoo_endpoint(client: TestClient):
    mock_snapshot = {
        "ticker": "GOOG",
        "period": "1y",
        "curl_cffi_available": True,
        "session_type": "curl_cffi.chrome",
        "steps": [],
    }

    with patch(
        "app.services.market_data_service.MarketDataService.fetch_debug_snapshot",
        return_value=mock_snapshot,
    ):
        response = client.get("/debug/yahoo/GOOG")

    assert response.status_code == 200
    assert response.json()["ticker"] == "GOOG"


def test_debug_filing_endpoint(client: TestClient):
    mock_diagnostics = {
        "accession_number": "0000320193-26-000013",
        "sec_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000013/aapl-20260328.htm",
        "selected_document": "aapl-20260328.htm",
        "raw_html_preview": "<html><body>Apple Inc.</body></html>",
        "extracted_text_preview": "MANAGEMENT'S DISCUSSION AND ANALYSIS",
        "xbrl_ratio": 0.01,
        "parser_diagnostics": {"parser": "beautifulsoup"},
        "xbrl_analysis": {"is_xbrl": False, "reasons": []},
    }

    with patch(
        "app.api.debug.SECService.inspect_primary_filing",
        new_callable=AsyncMock,
        return_value=(None, mock_diagnostics),
    ):
        response = client.get(
            "/debug/filing/0000320193-26-000013",
            params={"filing_type": "10-Q"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_document"] == "aapl-20260328.htm"
    assert body["xbrl_ratio"] == 0.01
    assert "parser_diagnostics" in body
