import json
from pathlib import Path

import pytest

from app.services.filing_document_service import (
    FilingIndexItem,
    FilingTextExtractor,
    PART_I_PATTERN,
    _first_pattern_match,
    analyze_xbrl_text,
    build_text_slices,
    find_marker_offsets,
    inspect_dom_for_missing_narrative,
    is_xbrl_attachment,
    looks_like_ix_hidden_leakage,
    looks_like_untrimmed_filing_content,
    looks_like_xbrl_text,
    normalize_filing_narrative_text,
    normalize_index_items,
    select_primary_document,
    starts_with_narrative_marker,
    trim_to_narrative,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def goog_index_payload() -> dict:
    return json.loads((FIXTURES_DIR / "goog_10q_index.json").read_text())


@pytest.fixture
def goog_primary_html() -> str:
    return (FIXTURES_DIR / "goog_10q_primary.html").read_text()


class TestPrimaryDocumentSelection:
    def test_selects_main_10q_html_not_xbrl(self, goog_index_payload):
        items = normalize_index_items(goog_index_payload)
        selected = select_primary_document(items, "10-Q", fallback_primary="goog-20240930.xml")

        assert selected == "goog-20240930.htm"

    def test_xbrl_attachments_are_ignored(self):
        assert is_xbrl_attachment("goog-20240930.xml") is True
        assert is_xbrl_attachment("goog-20240930_cal.xml") is True
        assert is_xbrl_attachment("goog-20240930_htm.xml") is True
        assert is_xbrl_attachment("goog-20240930.htm") is False

    def test_fallback_primary_xml_is_rejected(self, goog_index_payload):
        items = [item for item in normalize_index_items(goog_index_payload) if item.name.endswith(".htm") is False]
        with pytest.raises(ValueError, match="No primary HTML document found"):
            select_primary_document(items, "10-Q", fallback_primary="goog-20240930.xml")

    def test_prefers_type_match_over_larger_exhibit(self):
        items = [
            FilingIndexItem(name="exhibit991.htm", doc_type="EX-99.1", size=5000000),
            FilingIndexItem(name="goog-20240930.htm", doc_type="10-Q", size=1000),
        ]
        selected = select_primary_document(items, "10-Q")
        assert selected == "goog-20240930.htm"


class TestFilingTextExtraction:
    def test_extracts_management_discussion_from_goog_10q(self, goog_primary_html):
        text, diagnostics = FilingTextExtractor().extract_with_diagnostics(goog_primary_html, filing_type="10-Q")

        assert diagnostics.narrative_strategy == "10-q_from_part_i"
        assert text.startswith("PART I")
        assert "Management's Discussion and Analysis of Financial Condition and Results of Operations" in text
        assert "Revenue growth in Google Services" in text
        assert "us-gaap:Revenue" not in text
        assert "window.track" not in text
        assert "UNITED STATES" not in text[:200]

    def test_aapl_10k_extracts_from_part_i(self):
        html = (FIXTURES_DIR / "aapl_10k_sample.html").read_text(encoding="utf-8")
        text, diagnostics = FilingTextExtractor().extract_with_diagnostics(html, filing_type="10-K")

        assert diagnostics.narrative_strategy in {"10-k_from_part_i", "10-k_from_part_i_find"}
        assert diagnostics.first_part_i_offset is not None
        assert diagnostics.first_part_i_offset > 100
        assert diagnostics.first_item_1_offset is not None
        assert diagnostics.first_item_1a_offset is not None
        assert diagnostics.cover_page_tokens_removed > 0
        assert text.startswith("PART I")
        assert "Item 1. Business" in text[:300]
        assert "Item 1A. Risk Factors" in text
        assert "UNITED STATES" not in text
        assert "FORM 10-K" not in text[:100]

    def test_beautifulsoup_is_primary_parser(self, goog_primary_html):
        text, _ = FilingTextExtractor()._extract_with_beautifulsoup(goog_primary_html)
        assert "artificial intelligence" in text

    def test_goog_8k_extracts_narrative_from_first_item_section(self):
        html = (FIXTURES_DIR / "d57679d8k.htm").read_text(encoding="utf-8", errors="replace")
        text, diagnostics = FilingTextExtractor().extract_with_diagnostics(html, filing_type="8-K")

        assert diagnostics.removed_hidden_elements >= 1
        assert diagnostics.extraction_root == "body"
        assert diagnostics.narrative_strategy == "8k_from_first_item"
        assert diagnostics.first_item_decimal_offset is not None
        assert diagnostics.narrative_start_offset == diagnostics.first_item_offset
        assert diagnostics.first_item_heading.startswith("Item")
        assert diagnostics.first_item_offset is not None
        assert diagnostics.first_item_offset > 0
        assert diagnostics.cover_page_tokens_removed > 100
        assert diagnostics.preview_3000
        assert diagnostics.pre_trim_marker_offsets is not None
        assert diagnostics.pre_trim_marker_offsets.find_part_i == -1
        assert diagnostics.pre_trim_text_slices is not None
        assert diagnostics.final_text_slices is not None
        assert diagnostics.pre_trim_text_length > diagnostics.extracted_text_length
        assert text.startswith("Item")
        assert "Departure of Directors" in text[:500]
        assert "UNITED STATES" not in text
        assert "shareholder proposal" in text
        assert "SIGNATURE" in text
        assert not looks_like_ix_hidden_leakage(text)

    def test_ix_hidden_leakage_detection(self):
        leaked = "Depositary Shares, each representing a 1/20th interest\nfalse\n0001652044\n2026-06-05"
        assert looks_like_ix_hidden_leakage(leaked) is True
        assert looks_like_ix_hidden_leakage("Item 5.02 Departure of Directors") is False

    def test_marker_offsets_and_text_slices(self):
        text = "Cover\nPART I\nItem 1. Business\nItem 1A. Risk Factors\n" + ("x" * 40000)
        offsets = find_marker_offsets(text)
        assert offsets.find_part_i == 6
        assert offsets.find_item_1 == 13
        assert offsets.find_item_1a == 30
        assert offsets.find_risk_factors == 39

        slices = build_text_slices(text)
        assert len(slices.preview_5000) == 5000
        assert len(slices.chars_30000_35000) == 5000
        assert len(slices.chars_35000_40000) == 5000

    def test_dom_inspection_runs_when_part_i_missing(self):
        html = "<html><body><p>UNITED STATES</p><p>FORM 10-K</p></body></html>"
        inspection = inspect_dom_for_missing_narrative(html, "10-K")
        assert inspection.part_i_in_raw_html is False
        assert inspection.part_i_in_visible_text is False
        assert inspection.likely_issues

    def test_trims_8k_without_filing_type(self):
        cover = (
            "UNITED STATES\n\nSECURITIES AND EXCHANGE COMMISSION\n\nFORM\n\n8-K\n\n"
            "Apple Inc.\n\nCalifornia\n\n"
        )
        narrative = "Item 2.02 Results of Operations and Financial Condition.\n\nOn April 30, 2026..."
        text = cover + narrative
        trimmed, stats = trim_to_narrative(text, None)
        assert stats["narrative_strategy"] == "auto_from_first_item"
        assert trimmed.startswith("Item 2.02")
        assert "UNITED STATES" not in trimmed
        assert looks_like_untrimmed_filing_content(text, "8-K") is True
        assert looks_like_untrimmed_filing_content(trimmed, "8-K") is False

    def test_normalize_filing_narrative_text_trims_stored_cover_page(self):
        cover = (
            "UNITED STATES\n\nSECURITIES AND EXCHANGE COMMISSION\n\nFORM\n\n8-K\n\n"
            "Apple Inc.\n\nCalifornia\n\n"
        )
        narrative = "Item 2.02 Results of Operations and Financial Condition.\n\nPress release text.\n\nSIGNATURE"
        stored = cover + narrative
        normalized = normalize_filing_narrative_text(
            extracted_text=stored,
            raw_content=stored,
            raw_html=None,
            filing_type="8-K",
        )
        assert normalized is not None
        assert normalized.startswith("Item 2.02")
        assert starts_with_narrative_marker(normalized, "8-K")

    def test_excludes_ixbrl_report_html_from_primary_selection(self):
        items = [
            FilingIndexItem(name="R1.htm", doc_type="", size=200000),
            FilingIndexItem(name="d57679d8k.htm", doc_type="8-K", size=119785),
        ]
        selected = select_primary_document(items, "8-K")
        assert selected == "d57679d8k.htm"

    def test_part_i_pattern_does_not_match_part_ii(self):
        text = "PART II\nItem 7. MD&A"
        offset, heading = _first_pattern_match(PART_I_PATTERN, text)
        assert offset is None

        text = "Cover page\nPART I\nItem 1. Business"
        offset, heading = _first_pattern_match(PART_I_PATTERN, text)
        assert offset is not None
        assert heading == "PART I"

    def test_regex_fallback_still_extracts_text(self):
        html = "<html><body><p>Fallback parser text about quarterly results.</p></body></html>"
        text = FilingTextExtractor()._extract_with_regex(html)
        assert "Fallback parser text about quarterly results." in text

    def test_looks_like_xbrl_text_detects_taxonomy_tags(self):
        assert looks_like_xbrl_text("us-gaap:Revenue us-gaap:AccruedLiabilitiesCurrent") is True
        assert looks_like_xbrl_text("Management's Discussion and Analysis of financial results.") is False

    def test_analyze_xbrl_text_returns_diagnostics(self):
        analysis = analyze_xbrl_text(
            "us-gaap:Revenue us-gaap:AccruedLiabilitiesCurrent goog:A2.75SeniorNotesDue2031Member"
        )

        assert analysis.is_xbrl is True
        assert analysis.xbrl_token_ratio > 0
        assert analysis.xbrl_token_count >= 3
        assert analysis.reasons
        assert len(analysis.top_tokens) <= 20
        assert "us-gaap:Revenue" in analysis.preview_1000

    def test_analyze_xbrl_text_allows_prose_with_inline_tags(self):
        prose = (
            "MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS. "
            "Revenue increased during the quarter driven by strong services growth. "
            "The company continues to invest in artificial intelligence and cloud infrastructure."
        )
        analysis = analyze_xbrl_text(prose)

        assert analysis.is_xbrl is False
        assert analysis.reasons == []
