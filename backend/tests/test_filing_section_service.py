from pathlib import Path

import pytest

from app.services.filing_section_service import (
    build_navigation,
    parse_filing_reader_document,
    search_reader_document,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def goog_primary_html() -> str:
    return (FIXTURES_DIR / "goog_10q_primary.html").read_text()


@pytest.fixture
def aapl_10k_html() -> str:
    return (FIXTURES_DIR / "aapl_10k_sample.html").read_text(encoding="utf-8")


@pytest.fixture
def goog_8k_html() -> str:
    return (FIXTURES_DIR / "d57679d8k.htm").read_text(encoding="utf-8", errors="replace")


class TestFilingSectionParser:
    def test_parses_10q_items_with_table(self, goog_primary_html):
        document = parse_filing_reader_document(
            raw_html=goog_primary_html,
            extracted_text=None,
            raw_content=None,
            filing_type="10-Q",
        )

        assert document.cover_page is not None
        assert "UNITED STATES" in document.cover_page.content_text
        assert len(document.sections) >= 3
        item_keys = [section.item_key for section in document.sections]
        assert any(key.startswith("PART-") for key in item_keys)
        assert "1" in item_keys
        financial_section = next(section for section in document.sections if section.item_key == "1")
        assert "Financial Statements" in financial_section.title
        assert "<table" in financial_section.content_html
        assert "Revenues" in financial_section.content_text
        assert any("MD&A" in section.title or "Management" in section.title for section in document.sections)

    def test_parses_10k_items(self, aapl_10k_html):
        document = parse_filing_reader_document(
            raw_html=aapl_10k_html,
            extracted_text=None,
            raw_content=None,
            filing_type="10-K",
        )

        item_keys = [section.item_key for section in document.sections]
        assert "1" in item_keys
        assert "1A" in item_keys
        assert "7" in item_keys
        assert document.cover_page is not None
        assert "FORM 10-K" in document.cover_page.content_text

    def test_parses_8k_decimal_items(self, goog_8k_html):
        document = parse_filing_reader_document(
            raw_html=goog_8k_html,
            extracted_text=None,
            raw_content=None,
            filing_type="8-K",
        )

        assert document.sections
        assert document.sections[0].item_key in {"5.02", "5", "502"} or document.sections[0].title.startswith("Item")
        assert document.cover_page is not None or document.sections[0].content_text.startswith("Item")

    def test_text_fallback_splits_items(self):
        text = (
            "UNITED STATES\nFORM 8-K\n\n"
            "Item 2.02 Results of Operations and Financial Condition.\n\n"
            "Apple issued a press release.\n\n"
            "Item 9.01 Financial Statements and Exhibits.\n\n"
            "Exhibit 99.1 attached.\n"
        )
        document = parse_filing_reader_document(
            raw_html=None,
            extracted_text=text,
            raw_content=text,
            filing_type="8-K",
        )

        assert len(document.sections) == 2
        assert document.sections[0].item_key == "2.02"
        assert document.sections[1].item_key == "9.01"

    def test_search_reader_document_finds_keyword(self):
        document = parse_filing_reader_document(
            raw_html=None,
            extracted_text="Item 2.02 Results.\n\nRevenue increased significantly.\n",
            raw_content=None,
            filing_type="8-K",
        )
        matches = search_reader_document(document, "Revenue")
        assert len(matches) == 1

    def test_build_navigation_for_10q(self, goog_primary_html):
        document = parse_filing_reader_document(
            raw_html=goog_primary_html,
            extracted_text=None,
            raw_content=None,
            filing_type="10-Q",
        )
        navigation = build_navigation(document)
        assert any("PART I" in item["title"] for item in navigation)
        assert any("Item 1" in item["title"] for item in navigation)
