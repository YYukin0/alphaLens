import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from app.core.logging import get_logger

logger = get_logger(__name__)

XBRL_EXTENSIONS = (".xml", ".xsd", ".xsl", ".json")
XBRL_NAME_MARKERS = (
    "_cal.xml",
    "_def.xml",
    "_lab.xml",
    "_pre.xml",
    "_htm.xml",
    "instance",
    "schema",
    "linkbase",
)
EXHIBIT_PATTERN = re.compile(r"ex[-_]?\d", re.IGNORECASE)
IXBRL_REPORT_HTML_PATTERN = re.compile(r"^r\d+\.htm$", re.IGNORECASE)
PART_I_PATTERN = re.compile(r"\bPART\s+I(?!I\b)", re.IGNORECASE)
ITEM_1_PATTERN = re.compile(r"\bItem\s+1(?:[\.\s]|$)(?!\d)", re.IGNORECASE)
ITEM_1A_PATTERN = re.compile(r"\bItem\s+1A\b", re.IGNORECASE)
TABLE_OF_CONTENTS_PATTERN = re.compile(r"\bTABLE\s+OF\s+CONTENTS\b", re.IGNORECASE)
ITEM_HEADING_PATTERN = re.compile(r"Item\s*[\u2009\u202f]?\s*\d+\.\d+\.?", re.IGNORECASE)
XBRL_TAG_PATTERN = re.compile(r"\b[a-z0-9-]+:[A-Za-z][A-Za-z0-9._-]*\b")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
HIDDEN_STYLE_PATTERN = re.compile(r"display\s*:\s*none", re.IGNORECASE)
IXBRL_METADATA_TAG_NAMES = frozenset(
    {
        "ix:header",
        "ix:hidden",
        "ix:references",
        "ix:resources",
        "link:schemaref",
        "xbrli:context",
        "xbrli:entity",
        "xbrli:identifier",
        "xbrli:period",
        "xbrli:segment",
        "xbrli:startdate",
        "xbrli:enddate",
        "xbrldi:explicitmember",
    }
)


@dataclass
class FilingIndexItem:
    name: str
    doc_type: str
    size: int
    description: str = ""


@dataclass
class XbrlTextAnalysis:
    is_xbrl: bool
    xbrl_token_ratio: float
    total_tokens: int
    xbrl_token_count: int
    colon_tag_count: int
    reasons: list[str] = field(default_factory=list)
    top_tokens: list[dict[str, int]] = field(default_factory=list)
    preview_1000: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NarrativeMarkerOffsets:
    """Literal and case-insensitive str.find offsets on extracted text."""

    find_part_i: int = -1
    find_part_i_insensitive: int = -1
    find_item_1: int = -1
    find_item_1_insensitive: int = -1
    find_item_1a: int = -1
    find_item_1a_insensitive: int = -1
    find_risk_factors: int = -1
    find_risk_factors_insensitive: int = -1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionTextSlices:
    preview_5000: str = ""
    chars_30000_35000: str = ""
    chars_35000_40000: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DomNarrativeInspection:
    filing_type: str | None = None
    part_i_in_raw_html: bool = False
    part_i_in_visible_text: bool = False
    item_1_in_visible_text: bool = False
    hidden_display_none_count: int = 0
    ix_header_count: int = 0
    ix_hidden_count: int = 0
    xbrli_context_count: int = 0
    visible_body_text_length: int = 0
    full_body_text_length: int = 0
    likely_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionDiagnostics:
    parser: str
    html_length: int
    extracted_text_length: int
    word_count: int
    preview_1000: str
    extraction_root: str = "body"
    removed_hidden_elements: int = 0
    removed_ixbrl_metadata_tags: int = 0
    unwrapped_namespaced_tags: int = 0
    preview_3000: str = ""
    first_item_heading: str | None = None
    first_item_offset: int | None = None
    first_part_i_offset: int | None = None
    first_part_i_heading: str | None = None
    first_item_1_offset: int | None = None
    first_item_1_heading: str | None = None
    first_item_1a_offset: int | None = None
    first_item_1a_heading: str | None = None
    first_item_decimal_offset: int | None = None
    first_item_decimal_heading: str | None = None
    narrative_start_offset: int | None = None
    narrative_start_heading: str | None = None
    cover_page_tokens_removed: int = 0
    narrative_strategy: str = "full_body"
    detected_filing_type: str | None = None
    pre_trim_text_length: int = 0
    pre_trim_marker_offsets: NarrativeMarkerOffsets | None = None
    pre_trim_text_slices: ExtractionTextSlices | None = None
    final_marker_offsets: NarrativeMarkerOffsets | None = None
    final_text_slices: ExtractionTextSlices | None = None
    dom_narrative_inspection: DomNarrativeInspection | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in (
            "pre_trim_marker_offsets",
            "pre_trim_text_slices",
            "final_marker_offsets",
            "final_text_slices",
            "dom_narrative_inspection",
        ):
            value = payload.get(key)
            if value is None:
                continue
            if isinstance(value, dict):
                payload[key] = value
        return payload


def is_xbrl_attachment(filename: str) -> bool:
    lower = filename.lower()
    if lower.endswith(XBRL_EXTENSIONS):
        return True
    return any(marker in lower for marker in XBRL_NAME_MARKERS)


def is_html_document(filename: str) -> bool:
    return filename.lower().endswith((".htm", ".html"))


def is_ixbrl_report_html(filename: str) -> bool:
    """Exclude inline XBRL renderer pages such as R1.htm."""
    return bool(IXBRL_REPORT_HTML_PATTERN.match(filename.split("/")[-1]))


IX_HIDDEN_LEAK_PATTERN = re.compile(
    r"^Depositary Shares|^false\s*$|^0{3}\d{7}\s*$|^\d{4}-\d{2}-\d{2}\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def looks_like_ix_hidden_leakage(text: str | None) -> bool:
    """True when extracted text still begins with inline XBRL hidden-fact junk."""
    if not text:
        return False
    sample = text[:1200].strip()
    if ITEM_HEADING_PATTERN.search(sample[:400]):
        return False
    if PART_I_PATTERN.search(sample[:400]):
        return False
    if sample.startswith("UNITED STATES"):
        return False
    if sample.startswith("Depositary Shares"):
        return True
    lines = [line.strip() for line in sample.splitlines() if line.strip()]
    if len(lines) >= 2 and lines[0].startswith("Depositary Shares"):
        return True
    if "0001652044" in sample[:500] and "false" in sample[:500].lower():
        return True
    if re.match(r"^0{3}\d{7}\b", sample):
        return True
    return bool(IX_HIDDEN_LEAK_PATTERN.match(sample))


def looks_like_8k_cover_page(text: str | None) -> bool:
    if not text:
        return False
    if looks_like_ix_hidden_leakage(text):
        return True
    sample = text[:4000]
    if ITEM_HEADING_PATTERN.search(sample[:300]):
        return False
    if sample.startswith("Cover Page") or "Entity Information" in sample[:800]:
        return True
    return sample.startswith("UNITED STATES") and "SECURITIES AND EXCHANGE COMMISSION" in sample[:500]


def looks_like_sec_cover_page(text: str | None, filing_type: str | None = None) -> bool:
    """True when extracted text still begins with SEC cover page instead of narrative."""
    if not text:
        return False

    sample = text[:2500]
    if starts_with_narrative_marker(sample, filing_type):
        return False

    if sample.startswith("Cover Page") or "Entity Information" in sample[:800]:
        return True
    if sample.startswith("UNITED STATES") and "SECURITIES AND EXCHANGE COMMISSION" in sample[:800]:
        return True
    if re.search(r"(?m)^FORM\s*\n?\s*8-K\b", sample[:1200], re.IGNORECASE):
        return True
    if "CURRENT REPORT" in sample[:1200] and "Pursuant to Section" in sample[:1200]:
        if not ITEM_HEADING_PATTERN.search(sample[:800]):
            return True
    return looks_like_8k_cover_page(text) if (filing_type or "").upper() == "8-K" else False


def starts_with_narrative_marker(text: str, filing_type: str | None = None) -> bool:
    sample = text[:160].lstrip()
    if not sample:
        return False
    ft = (filing_type or "").upper()
    if ft == "8-K":
        return ITEM_HEADING_PATTERN.match(sample) is not None
    if ft in {"10-K", "10-Q"}:
        return (
            PART_I_PATTERN.match(sample) is not None
            or ITEM_1_PATTERN.match(sample) is not None
        )
    return (
        ITEM_HEADING_PATTERN.match(sample) is not None
        or PART_I_PATTERN.match(sample) is not None
        or ITEM_1_PATTERN.match(sample) is not None
    )


def _auto_narrative_trim_candidates(text: str) -> list[tuple[int, str, str]]:
    markers = find_narrative_markers(text)
    marker_offsets = find_marker_offsets(text)
    candidates: list[tuple[int, str, str]] = []

    if markers["first_item_decimal_offset"] is not None:
        offset = int(markers["first_item_decimal_offset"])
        candidates.append(
            (
                offset,
                str(markers["first_item_decimal_heading"] or text[offset : offset + 24]).strip(),
                "auto_from_first_item",
            )
        )
    if marker_offsets.find_part_i_insensitive >= 0:
        offset = marker_offsets.find_part_i_insensitive
        candidates.append((offset, text[offset : offset + 6].strip(), "auto_from_part_i"))
    if markers["first_item_1_offset"] is not None:
        offset = int(markers["first_item_1_offset"])
        candidates.append(
            (
                offset,
                str(markers["first_item_1_heading"] or text[offset : offset + 16]).strip(),
                "auto_from_item_1",
            )
        )
    return sorted(candidates, key=lambda item: item[0])


def normalize_filing_narrative_text(
    *,
    extracted_text: str | None,
    raw_content: str | None,
    raw_html: str | None,
    filing_type: str | None,
) -> str | None:
    """Return narrative-only filing text, re-parsing HTML when stored text is still a cover page."""
    source = extracted_text or raw_content
    if source:
        trimmed, stats = trim_to_narrative(source, filing_type)
        if int(stats.get("narrative_start_offset") or 0) > 0:
            return trimmed
        if starts_with_narrative_marker(trimmed, filing_type):
            return trimmed
        if not looks_like_sec_cover_page(trimmed, filing_type) and not looks_like_ix_hidden_leakage(trimmed):
            return trimmed

    if raw_html:
        text, _ = FilingTextExtractor().extract_with_diagnostics(raw_html, filing_type=filing_type)
        return text or None

    if source:
        return trim_to_narrative(source, filing_type)[0]
    return None


def looks_like_untrimmed_filing_content(text: str | None, filing_type: str | None = None) -> bool:
    if not text:
        return False
    if looks_like_ix_hidden_leakage(text):
        return True
    if looks_like_sec_cover_page(text, filing_type):
        return True
    _, stats = trim_to_narrative(text, filing_type)
    return int(stats.get("narrative_start_offset") or 0) > 0


def _first_pattern_match(pattern: re.Pattern[str], text: str) -> tuple[int | None, str | None]:
    match = pattern.search(text)
    if not match:
        return None, None
    return match.start(), match.group(0).strip()


def _slice_text_window(text: str, start: int, end: int) -> str:
    if not text or start >= len(text):
        return ""
    return text[start:min(end, len(text))]


def build_text_slices(text: str) -> ExtractionTextSlices:
    return ExtractionTextSlices(
        preview_5000=text[:5000],
        chars_30000_35000=_slice_text_window(text, 30000, 35000),
        chars_35000_40000=_slice_text_window(text, 35000, 40000),
    )


def find_marker_offsets(text: str) -> NarrativeMarkerOffsets:
    upper = text.upper()
    return NarrativeMarkerOffsets(
        find_part_i=text.find("PART I"),
        find_part_i_insensitive=upper.find("PART I"),
        find_item_1=text.find("Item 1"),
        find_item_1_insensitive=upper.find("ITEM 1"),
        find_item_1a=text.find("Item 1A"),
        find_item_1a_insensitive=upper.find("ITEM 1A"),
        find_risk_factors=text.find("Risk Factors"),
        find_risk_factors_insensitive=upper.find("RISK FACTORS"),
    )


def log_extraction_diagnostics(
    *,
    accession_number: str,
    selected_document: str,
    filing_type: str | None,
    diagnostics: ExtractionDiagnostics,
    pre_trim_text: str | None = None,
) -> None:
    pre_trim = pre_trim_text or ""
    pre_offsets = diagnostics.pre_trim_marker_offsets or find_marker_offsets(pre_trim)
    final_offsets = diagnostics.final_marker_offsets or NarrativeMarkerOffsets()
    pre_slices = diagnostics.pre_trim_text_slices or build_text_slices(pre_trim)
    final_slices = diagnostics.final_text_slices or ExtractionTextSlices()
    logger.info(
        "filing_extraction_diagnostics",
        accession_number=accession_number,
        selected_document=selected_document,
        filing_type=filing_type or diagnostics.detected_filing_type,
        parser=diagnostics.parser,
        narrative_strategy=diagnostics.narrative_strategy,
        pre_trim_text_length=diagnostics.pre_trim_text_length,
        extracted_text_length=diagnostics.extracted_text_length,
        removed_hidden_elements=diagnostics.removed_hidden_elements,
        removed_ixbrl_metadata_tags=diagnostics.removed_ixbrl_metadata_tags,
        pre_trim_find_part_i=pre_offsets.find_part_i,
        pre_trim_find_item_1=pre_offsets.find_item_1,
        pre_trim_find_item_1a=pre_offsets.find_item_1a,
        pre_trim_find_risk_factors=pre_offsets.find_risk_factors,
        pre_trim_find_part_i_insensitive=pre_offsets.find_part_i_insensitive,
        pre_trim_find_item_1_insensitive=pre_offsets.find_item_1_insensitive,
        pre_trim_find_item_1a_insensitive=pre_offsets.find_item_1a_insensitive,
        pre_trim_find_risk_factors_insensitive=pre_offsets.find_risk_factors_insensitive,
        final_find_part_i=final_offsets.find_part_i,
        final_find_item_1=final_offsets.find_item_1,
        final_find_item_1a=final_offsets.find_item_1a,
        final_find_risk_factors=final_offsets.find_risk_factors,
        narrative_start_offset=diagnostics.narrative_start_offset,
        cover_page_tokens_removed=diagnostics.cover_page_tokens_removed,
        pre_trim_preview_5000=pre_slices.preview_5000,
        pre_trim_chars_30000_35000=pre_slices.chars_30000_35000,
        pre_trim_chars_35000_40000=pre_slices.chars_35000_40000,
        final_preview_5000=final_slices.preview_5000,
        final_chars_30000_35000=final_slices.chars_30000_35000,
        final_chars_35000_40000=final_slices.chars_35000_40000,
        dom_narrative_inspection=(
            diagnostics.dom_narrative_inspection.to_dict() if diagnostics.dom_narrative_inspection else None
        ),
    )


def inspect_dom_for_missing_narrative(html: str, filing_type: str | None) -> DomNarrativeInspection:
    ft = (filing_type or "").upper()
    inspection = DomNarrativeInspection(filing_type=filing_type)
    issues: list[str] = []

    raw_upper = html.upper()
    inspection.part_i_in_raw_html = "PART I" in raw_upper or "PART&nbsp;I" in raw_upper.replace(" ", "")

    soup = BeautifulSoup(html, "html.parser")
    inspection.hidden_display_none_count = sum(
        1 for tag in soup.find_all(True) if FilingTextExtractor._is_hidden_element(tag)
    )
    inspection.ix_header_count = len(soup.find_all(lambda tag: tag.name and tag.name.lower() == "ix:header"))
    inspection.ix_hidden_count = len(soup.find_all(lambda tag: tag.name and tag.name.lower() == "ix:hidden"))
    inspection.xbrli_context_count = len(
        soup.find_all(lambda tag: tag.name and tag.name.lower() == "xbrli:context")
    )

    full_root = soup.body or soup
    inspection.full_body_text_length = len(full_root.get_text("\n", strip=True))

    prepared = BeautifulSoup(html, "html.parser")
    prep_stats = FilingTextExtractor._prepare_soup_for_extraction(prepared)
    visible_root = prepared.body or prepared
    visible_text = FilingTextExtractor._normalize_text(visible_root.get_text("\n", strip=True))
    inspection.visible_body_text_length = len(visible_text)

    visible_upper = visible_text.upper()
    inspection.part_i_in_visible_text = PART_I_PATTERN.search(visible_text) is not None
    inspection.item_1_in_visible_text = ITEM_1_PATTERN.search(visible_text) is not None

    if inspection.hidden_display_none_count == 0 and inspection.ix_header_count > 0:
        issues.append("ix:header present but no display:none hidden wrapper detected")
    if inspection.full_body_text_length > 0 and inspection.visible_body_text_length == 0:
        issues.append("body text empty after hidden/metadata removal")
    if inspection.part_i_in_raw_html and not inspection.part_i_in_visible_text and ft in {"10-K", "10-Q"}:
        issues.append("PART I exists in raw HTML but not in visible text after DOM cleanup")
    if not inspection.part_i_in_raw_html and not inspection.item_1_in_visible_text and ft in {"10-K", "10-Q"}:
        issues.append("PART I and Item 1 not found in HTML or visible extracted text")
    if inspection.ix_hidden_count > 0 and int(prep_stats.get("removed_hidden_elements", 0)) == 0:
        issues.append("ix:hidden tags remain because hidden wrapper was not removed")
    if inspection.full_body_text_length > inspection.visible_body_text_length * 3:
        issues.append(
            f"large hidden/metadata block ({inspection.full_body_text_length - inspection.visible_body_text_length} chars removed)"
        )

    inspection.likely_issues = issues
    return inspection


def find_narrative_markers(text: str) -> dict[str, int | str | None]:
    part_i_offset, part_i_heading = _first_pattern_match(PART_I_PATTERN, text)
    item_1_offset, item_1_heading = _first_pattern_match(ITEM_1_PATTERN, text)
    item_1a_offset, item_1a_heading = _first_pattern_match(ITEM_1A_PATTERN, text)
    item_decimal_offset, item_decimal_heading = _first_pattern_match(ITEM_HEADING_PATTERN, text)
    toc_offset, toc_heading = _first_pattern_match(TABLE_OF_CONTENTS_PATTERN, text)

    return {
        "first_part_i_offset": part_i_offset,
        "first_part_i_heading": part_i_heading,
        "first_item_1_offset": item_1_offset,
        "first_item_1_heading": item_1_heading,
        "first_item_1a_offset": item_1a_offset,
        "first_item_1a_heading": item_1a_heading,
        "first_table_of_contents_offset": toc_offset,
        "first_table_of_contents_heading": toc_heading,
        "first_item_decimal_offset": item_decimal_offset,
        "first_item_decimal_heading": item_decimal_heading,
    }


def trim_to_narrative(text: str, filing_type: str | None) -> tuple[str, dict[str, int | str | None]]:
    markers = find_narrative_markers(text)
    stats: dict[str, int | str | None] = {
        **markers,
        "cover_page_tokens_removed": 0,
        "narrative_strategy": "full_body",
        "narrative_start_offset": None,
        "narrative_start_heading": None,
        "first_item_heading": None,
        "first_item_offset": None,
    }

    ft = (filing_type or "").upper()
    trim_offset: int | None = None
    trim_heading: str | None = None
    strategy = "full_body"

    if ft in {"10-K", "10-Q"}:
        part_i_find = find_marker_offsets(text).find_part_i_insensitive
        if part_i_find >= 0 and (markers["first_part_i_offset"] is None or part_i_find < int(markers["first_part_i_offset"])):
            trim_offset = part_i_find
            trim_heading = text[part_i_find : part_i_find + 6].strip()
            strategy = f"{ft.lower()}_from_part_i_find"
        elif markers["first_part_i_offset"] is not None:
            trim_offset = int(markers["first_part_i_offset"])
            trim_heading = str(markers["first_part_i_heading"])
            strategy = f"{ft.lower()}_from_part_i"
        elif markers["first_item_1_offset"] is not None:
            trim_offset = int(markers["first_item_1_offset"])
            trim_heading = str(markers["first_item_1_heading"])
            strategy = f"{ft.lower()}_from_item_1"
        elif markers["first_table_of_contents_offset"] is not None:
            trim_offset = int(markers["first_table_of_contents_offset"])
            trim_heading = str(markers["first_table_of_contents_heading"])
            strategy = f"{ft.lower()}_from_table_of_contents"
    elif ft == "8-K":
        if markers["first_item_decimal_offset"] is not None:
            trim_offset = int(markers["first_item_decimal_offset"])
            trim_heading = str(markers["first_item_decimal_heading"])
            strategy = "8k_from_first_item"
        elif looks_like_8k_cover_page(text):
            strategy = "8k_cover_page_no_item_found"

    if trim_offset is None:
        auto_candidates = _auto_narrative_trim_candidates(text)
        if auto_candidates:
            trim_offset, trim_heading, strategy = auto_candidates[0]

    if trim_offset is not None and trim_offset > 0:
        stats["narrative_start_offset"] = trim_offset
        stats["narrative_start_heading"] = trim_heading
        stats["first_item_offset"] = trim_offset
        stats["first_item_heading"] = trim_heading
        stats["cover_page_tokens_removed"] = len(_tokenize(text[:trim_offset]))
        stats["narrative_strategy"] = strategy
        return text[trim_offset:].lstrip(), stats

    stats["narrative_strategy"] = strategy
    return text, stats


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text)


def analyze_xbrl_text(
    text: str | None,
    preview_len: int = 1000,
    top_token_count: int = 20,
) -> XbrlTextAnalysis:
    if not text:
        return XbrlTextAnalysis(
            is_xbrl=False,
            xbrl_token_ratio=0.0,
            total_tokens=0,
            xbrl_token_count=0,
            colon_tag_count=0,
            reasons=["empty_text"],
            top_tokens=[],
            preview_1000="",
        )

    sample = text[:20000]
    preview = text[:preview_len]
    tokens = _tokenize(sample)
    xbrl_tokens = XBRL_TAG_PATTERN.findall(sample)
    xbrl_token_set = set(xbrl_tokens)
    total_tokens = len(tokens)
    xbrl_token_count = len(xbrl_tokens)
    xbrl_token_ratio = xbrl_token_count / total_tokens if total_tokens else 0.0
    colon_tag_count = sample.count(":")

    token_counts = Counter(token.lower() for token in tokens if len(token) > 1)
    top_tokens = [
        {"token": token, "count": count}
        for token, count in token_counts.most_common(top_token_count)
    ]

    reasons: list[str] = []
    if "xmlns:" in sample:
        reasons.append("contains xmlns: marker")
    if "xbrli:" in sample:
        reasons.append("contains xbrli: marker")

    if total_tokens == 0:
        reasons.append("no_tokens_found")
    elif xbrl_token_ratio >= 0.20:
        reasons.append(f"xbrl_token_ratio {xbrl_token_ratio:.4f} >= 0.20")
    elif xbrl_token_count >= 50 and xbrl_token_ratio >= 0.08:
        reasons.append(
            f"xbrl_token_count {xbrl_token_count} >= 50 and xbrl_token_ratio {xbrl_token_ratio:.4f} >= 0.08"
        )
    elif xbrl_token_ratio >= 0.45 and total_tokens < 200:
        reasons.append(
            f"short_text_with_high_xbrl_ratio ({xbrl_token_ratio:.4f} across {total_tokens} tokens)"
        )
    elif len(xbrl_token_set) >= 20 and xbrl_token_ratio >= 0.12 and total_tokens < 500:
        reasons.append(
            f"diverse_xbrl_taxonomy_tokens ({len(xbrl_token_set)} unique tags, ratio {xbrl_token_ratio:.4f})"
        )

    return XbrlTextAnalysis(
        is_xbrl=len(reasons) > 0,
        xbrl_token_ratio=round(xbrl_token_ratio, 4),
        total_tokens=total_tokens,
        xbrl_token_count=xbrl_token_count,
        colon_tag_count=colon_tag_count,
        reasons=reasons,
        top_tokens=top_tokens,
        preview_1000=preview,
    )


def looks_like_xbrl_text(text: str | None) -> bool:
    return analyze_xbrl_text(text).is_xbrl


def log_xbrl_rejection_diagnostics(
    *,
    accession_number: str,
    selected_document: str,
    extracted_text: str,
    parser_diagnostics: ExtractionDiagnostics | None = None,
) -> XbrlTextAnalysis:
    analysis = analyze_xbrl_text(extracted_text)
    logger.error(
        "filing_extraction_xbrl_rejected",
        accession_number=accession_number,
        selected_document=selected_document,
        extracted_text_length=len(extracted_text),
        extracted_text_preview=analysis.preview_1000,
        xbrl_token_ratio=analysis.xbrl_token_ratio,
        xbrl_token_count=analysis.xbrl_token_count,
        total_tokens=analysis.total_tokens,
        top_tokens=analysis.top_tokens,
        classification_reasons=analysis.reasons,
        parser_diagnostics=parser_diagnostics.to_dict() if parser_diagnostics else None,
    )
    return analysis


def normalize_index_items(index_payload: dict[str, Any]) -> list[FilingIndexItem]:
    directory = index_payload.get("directory", {})
    raw_items = directory.get("item", [])
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    items: list[FilingIndexItem] = []
    for raw in raw_items:
        name = raw.get("name")
        if not name:
            continue
        size_raw = raw.get("size", 0)
        try:
            size = int(size_raw)
        except (TypeError, ValueError):
            size = 0
        items.append(
            FilingIndexItem(
                name=name,
                doc_type=str(raw.get("type", "")).strip(),
                size=size,
                description=str(raw.get("description", "")).strip(),
            )
        )
    return items


def select_primary_document(
    items: list[FilingIndexItem],
    filing_type: str,
    fallback_primary: str | None = None,
) -> str:
    """Choose the main HTML filing document and ignore XBRL attachments."""
    html_items = [
        item
        for item in items
        if is_html_document(item.name)
        and not is_xbrl_attachment(item.name)
        and not is_ixbrl_report_html(item.name)
    ]

    filing_type_upper = filing_type.upper()
    filing_type_token = filing_type_upper.replace("-", "").lower()

    def name_score(item: FilingIndexItem) -> tuple[int, int]:
        lower = item.name.lower()
        score = 0
        if filing_type_token and filing_type_token in lower:
            score += 100
        if filing_type_upper in lower:
            score += 100
        return score, item.size

    for item in html_items:
        if item.doc_type.upper() == filing_type_upper:
            logger.info("primary_document_selected", filename=item.name, reason="type_match")
            return item.name

    non_exhibit_items = [item for item in html_items if not EXHIBIT_PATTERN.search(item.name)]
    candidates = non_exhibit_items or html_items
    if candidates:
        selected = max(candidates, key=name_score)
        logger.info("primary_document_selected", filename=selected.name, reason="best_match_html")
        return selected.name

    if (
        fallback_primary
        and is_html_document(fallback_primary)
        and not is_xbrl_attachment(fallback_primary)
    ):
        logger.info("primary_document_selected", filename=fallback_primary, reason="fallback_primary")
        return fallback_primary

    raise ValueError(f"No primary HTML document found for filing type {filing_type}")


class FilingTextExtractor:
    """Extract readable text from SEC filing HTML."""

    def extract(self, html: str) -> str:
        text, _ = self.extract_with_diagnostics(html)
        return text

    def extract_with_diagnostics(
        self,
        html: str,
        filing_type: str | None = None,
    ) -> tuple[str, ExtractionDiagnostics]:
        detected_type = filing_type or self._detect_filing_type(html)
        pre_trim_text, prep_stats = self._extract_with_beautifulsoup(html, detected_type)
        parser = "beautifulsoup"
        text = pre_trim_text
        if not text or len(text.split()) <= 50:
            logger.warning("beautifulsoup_extract_short_fallback", words=len(text.split()) if text else 0)
            text = self._extract_with_regex(html)
            pre_trim_text = text
            parser = "regex_fallback"
            prep_stats = {
                "extraction_root": "body",
                "removed_hidden_elements": 0,
                "removed_ixbrl_metadata_tags": 0,
                "unwrapped_namespaced_tags": 0,
                "first_item_heading": None,
                "first_item_offset": None,
                "cover_page_tokens_removed": 0,
                "narrative_strategy": "regex_fallback",
            }

        pre_trim_marker_offsets = find_marker_offsets(pre_trim_text)
        pre_trim_text_slices = build_text_slices(pre_trim_text)
        dom_inspection: DomNarrativeInspection | None = None
        ft_upper = (detected_type or "").upper()
        if ft_upper in {"10-K", "10-Q"} and pre_trim_marker_offsets.find_part_i_insensitive < 0:
            dom_inspection = inspect_dom_for_missing_narrative(html, detected_type)

        text, narrative_stats = trim_to_narrative(pre_trim_text, detected_type or filing_type)
        prep_stats.update(narrative_stats)

        final_marker_offsets = find_marker_offsets(text)
        final_text_slices = build_text_slices(text)

        diagnostics = ExtractionDiagnostics(
            parser=parser,
            html_length=len(html),
            extracted_text_length=len(text),
            word_count=len(text.split()),
            preview_1000=text[:1000],
            preview_3000=text[:3000],
            extraction_root=str(prep_stats.get("extraction_root", "body")),
            removed_hidden_elements=int(prep_stats.get("removed_hidden_elements", 0)),
            removed_ixbrl_metadata_tags=int(prep_stats.get("removed_ixbrl_metadata_tags", 0)),
            unwrapped_namespaced_tags=int(prep_stats.get("unwrapped_namespaced_tags", 0)),
            first_item_heading=prep_stats.get("first_item_heading"),
            first_item_offset=prep_stats.get("first_item_offset"),
            first_part_i_offset=prep_stats.get("first_part_i_offset"),
            first_part_i_heading=prep_stats.get("first_part_i_heading"),
            first_item_1_offset=prep_stats.get("first_item_1_offset"),
            first_item_1_heading=prep_stats.get("first_item_1_heading"),
            first_item_1a_offset=prep_stats.get("first_item_1a_offset"),
            first_item_1a_heading=prep_stats.get("first_item_1a_heading"),
            first_item_decimal_offset=prep_stats.get("first_item_decimal_offset"),
            first_item_decimal_heading=prep_stats.get("first_item_decimal_heading"),
            narrative_start_offset=prep_stats.get("narrative_start_offset"),
            narrative_start_heading=prep_stats.get("narrative_start_heading"),
            cover_page_tokens_removed=int(prep_stats.get("cover_page_tokens_removed", 0)),
            narrative_strategy=str(prep_stats.get("narrative_strategy", "full_body")),
            detected_filing_type=detected_type,
            pre_trim_text_length=len(pre_trim_text),
            pre_trim_marker_offsets=pre_trim_marker_offsets,
            pre_trim_text_slices=pre_trim_text_slices,
            final_marker_offsets=final_marker_offsets,
            final_text_slices=final_text_slices,
            dom_narrative_inspection=dom_inspection,
        )
        return text, diagnostics

    @staticmethod
    def _detect_filing_type(html: str) -> str | None:
        soup = BeautifulSoup(html[:10000], "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        title_upper = title.upper()
        if "8-K" in title_upper:
            return "8-K"
        if "10-Q" in title_upper:
            return "10-Q"
        if "10-K" in title_upper:
            return "10-K"
        if re.search(r"\bFORM\s+10-K\b", html[:15000], re.IGNORECASE):
            return "10-K"
        if re.search(r"\bFORM\s+10-Q\b", html[:15000], re.IGNORECASE):
            return "10-Q"
        if re.search(r"\bFORM\s+8-K\b", html[:15000], re.IGNORECASE):
            return "8-K"
        return None

    @staticmethod
    def _is_hidden_element(tag) -> bool:
        attrs = getattr(tag, "attrs", None)
        if not attrs:
            return False

        style = attrs.get("style", "")
        if isinstance(style, list):
            style = " ".join(style)
        style_text = str(style)
        if HIDDEN_STYLE_PATTERN.search(style_text):
            return True
        if "sec-ix-hidden" in style_text.lower():
            return True

        for attr_name, attr_value in attrs.items():
            if "sec-ix-hidden" in str(attr_name).lower():
                return True
            if isinstance(attr_value, list):
                attr_value = " ".join(str(value) for value in attr_value)
            if "sec-ix-hidden" in str(attr_value).lower():
                return True
        return False

    @staticmethod
    def _prepare_soup_for_extraction(soup: BeautifulSoup) -> dict[str, int | str]:
        stats: dict[str, int | str] = {
            "extraction_root": "body",
            "removed_hidden_elements": 0,
            "removed_ixbrl_metadata_tags": 0,
            "unwrapped_namespaced_tags": 0,
        }

        for tag_name in ("script", "style", "noscript", "header", "footer", "meta", "link"):
            for tag in soup.find_all(tag_name):
                tag.decompose()

        for tag in list(soup.find_all(True)):
            if FilingTextExtractor._is_hidden_element(tag):
                tag.decompose()
                stats["removed_hidden_elements"] = int(stats["removed_hidden_elements"]) + 1

        for tag in list(soup.find_all(True)):
            tag_name = (tag.name or "").lower()
            if tag_name in IXBRL_METADATA_TAG_NAMES:
                tag.decompose()
                stats["removed_ixbrl_metadata_tags"] = int(stats["removed_ixbrl_metadata_tags"]) + 1

        for tag in list(soup.find_all(True)):
            if tag.name and ":" in tag.name:
                tag.unwrap()
                stats["unwrapped_namespaced_tags"] = int(stats["unwrapped_namespaced_tags"]) + 1

        return stats

    @staticmethod
    def _extract_with_beautifulsoup(
        html: str,
        filing_type: str | None = None,
    ) -> tuple[str, dict[str, int | str | None]]:
        soup = BeautifulSoup(html, "html.parser")
        prep_stats = FilingTextExtractor._prepare_soup_for_extraction(soup)

        root = soup.body or soup
        if soup.body is not None:
            prep_stats["extraction_root"] = "body"

        text = root.get_text("\n", strip=True)
        normalized = FilingTextExtractor._normalize_text(text)
        prep_stats.setdefault("first_item_heading", None)
        prep_stats.setdefault("first_item_offset", None)
        prep_stats.setdefault("cover_page_tokens_removed", 0)
        prep_stats.setdefault("narrative_strategy", "full_body")
        return normalized, prep_stats

    @staticmethod
    def _extract_with_regex(html: str) -> str:
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
        text = re.sub(r"(?s)<.*?>", " ", text)
        return FilingTextExtractor._normalize_text(text)

    @staticmethod
    def _strip_inline_xbrl_tokens(text: str) -> str:
        return XBRL_TAG_PATTERN.sub(" ", text)

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\xa0", " ")
        text = FilingTextExtractor._strip_inline_xbrl_tokens(text)
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        return "\n\n".join(lines)
