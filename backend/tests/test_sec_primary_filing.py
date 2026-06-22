import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.services.filing_document_service import normalize_index_items, select_primary_document
from app.services.sec_service import SECService
from app.config import Settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sec_service():
    return SECService(Settings(sec_user_agent="AlphaLens Test contact@test.local"))


@pytest.fixture
def goog_index_payload():
    return json.loads((FIXTURES_DIR / "goog_10q_index.json").read_text())


@pytest.fixture
def goog_primary_html():
    return (FIXTURES_DIR / "goog_10q_primary.html").read_text()


class TestSECPrimaryFilingDownload:
    @pytest.mark.asyncio
    async def test_download_primary_filing_uses_index_html(self, sec_service, goog_index_payload, goog_primary_html):
        items = normalize_index_items(goog_index_payload)
        assert select_primary_document(items, "10-Q", "goog-20240930.xml") == "goog-20240930.htm"

        with patch.object(sec_service, "fetch_filing_index", new_callable=AsyncMock, return_value=items):
            with patch.object(
                sec_service,
                "download_filing_content",
                new_callable=AsyncMock,
                return_value=goog_primary_html,
            ) as mock_download:
                content = await sec_service.download_primary_filing(
                    cik="1652044",
                    accession_number="0001652044-24-000123",
                    filing_type="10-Q",
                    fallback_primary="goog-20240930.xml",
                )

        assert content.primary_document == "goog-20240930.htm"
        assert content.extracted_text.startswith("PART I")
        assert "Management's Discussion and Analysis" in content.extracted_text
        assert "us-gaap:Revenue" not in content.extracted_text
        mock_download.assert_awaited_once()
        assert mock_download.await_args.args[0].endswith("goog-20240930.htm")

    @pytest.mark.asyncio
    async def test_download_primary_filing_rejects_xbrl_only_selection(self, sec_service):
        xbrl_items = normalize_index_items(
            {
                "directory": {
                    "item": [
                        {"name": "goog-20240930.xml", "type": "XML", "size": "100"},
                        {"name": "goog-20240930_cal.xml", "type": "XML", "size": "50"},
                    ]
                }
            }
        )

        with patch.object(sec_service, "fetch_filing_index", new_callable=AsyncMock, return_value=xbrl_items):
            with pytest.raises(ValueError, match="No primary HTML document found"):
                await sec_service.download_primary_filing(
                    cik="1652044",
                    accession_number="0001652044-24-000123",
                    filing_type="10-Q",
                    fallback_primary="goog-20240930.xml",
                )
