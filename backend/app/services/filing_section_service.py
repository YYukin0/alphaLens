import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger
from app.services.filing_document_service import (
    FilingTextExtractor,
    normalize_filing_narrative_text,
    trim_to_narrative,
)

logger = get_logger(__name__)

PARSER_VERSION = 1

ITEM_SECTION_HEADING = re.compile(
    r"^\s*Item\s+(\d+(?:\.\d+)?[A-Z]?)\s*[\.\u2009\u202f]?\s*(.*)$",
    re.IGNORECASE,
)
PART_HEADING = re.compile(r"^\s*PART\s+([IVXLC]+)\s*$", re.IGNORECASE)
SIGNATURE_HEADING = re.compile(r"^\s*SIGNATURES?\s*$", re.IGNORECASE)
BLOCK_TAGS = frozenset({"p", "h1", "h2", "h3", "h4", "h5", "h6", "table", "li"})
TABLE_CELL_TAGS = frozenset({"td", "th"})


@dataclass
class FilingCoverPage:
    content_html: str
    content_text: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class FilingSection:
    item_key: str
    title: str
    anchor_id: str
    content_html: str
    content_text: str
    order: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FilingReaderDocument:
    cover_page: FilingCoverPage | None = None
    sections: list[FilingSection] = field(default_factory=list)
    parser_version: int = PARSER_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "parser_version": self.parser_version,
            "cover_page": self.cover_page.to_dict() if self.cover_page else None,
            "sections": [section.to_dict() for section in self.sections],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "FilingReaderDocument | None":
        if not payload:
            return None
        cover = payload.get("cover_page")
        sections = [
            FilingSection(**section)
            for section in payload.get("sections", [])
        ]
        return cls(
            cover_page=FilingCoverPage(**cover) if cover else None,
            sections=sections,
            parser_version=int(payload.get("parser_version", PARSER_VERSION)),
        )


def serialize_reader_document(document: FilingReaderDocument) -> str:
    return json.dumps(document.to_dict())


def deserialize_reader_document(raw: str | None) -> FilingReaderDocument | None:
    if not raw:
        return None
    try:
        return FilingReaderDocument.from_dict(json.loads(raw))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("filing_sections_deserialize_failed", error=str(exc))
        return None


def _normalize_block_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _slugify_item_key(item_key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", item_key.lower()).strip("-") or "section"


def _is_section_heading(text: str) -> re.Match[str] | None:
    normalized = _normalize_block_text(text)
    if not normalized or len(normalized) > 240:
        return None
    match = ITEM_SECTION_HEADING.match(normalized)
    if match:
        return match
    return None


def _is_part_heading(text: str) -> re.Match[str] | None:
    normalized = _normalize_block_text(text)
    if not normalized or len(normalized) > 40:
        return None
    return PART_HEADING.match(normalized)


def _is_signature_heading(text: str) -> bool:
    return bool(SIGNATURE_HEADING.match(_normalize_block_text(text)))


def _is_leaf_block(tag: Tag) -> bool:
    if tag.name not in BLOCK_TAGS:
        return False
    if tag.find_parent("table") is not None:
        return False
    if tag.name == "div":
        return tag.find(["p", "table", "h1", "h2", "h3", "h4", "h5", "h6"]) is None
    return True


def _collect_blocks(root: Tag) -> list[tuple[str, Tag, str]]:
    blocks: list[tuple[str, Tag, str]] = []
    seen_tables: set[int] = set()

    for tag in root.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "table", "div", "li"]):
        if tag.find_parent("table") is not None:
            continue
        if tag.name == "table":
            tag_id = id(tag)
            if tag_id in seen_tables:
                continue
            seen_tables.add(tag_id)
            text = _normalize_block_text(tag.get_text("\n", strip=True))
            blocks.append(("table", tag, text))
            continue
        if not _is_leaf_block(tag):
            continue
        text = _normalize_block_text(tag.get_text("\n", strip=True))
        if text:
            blocks.append(("block", tag, text))
    return blocks


def _clean_table_html(table: Tag) -> str:
    cloned = BeautifulSoup(str(table), "html.parser").find("table")
    if cloned is None:
        return ""

    for hidden in cloned.find_all(True):
        if FilingTextExtractor._is_hidden_element(hidden):
            hidden.decompose()

    for tag in list(cloned.find_all(True)):
        tag_name = (tag.name or "").lower()
        if tag_name in {"script", "style", "ix:header", "ix:hidden"}:
            tag.decompose()
            continue
        if ":" in tag_name:
            tag.unwrap()
            continue
        allowed_attrs = {}
        if tag.name == "table":
            allowed_attrs["class"] = "filing-table"
        if tag.has_attr("colspan"):
            allowed_attrs["colspan"] = tag["colspan"]
        if tag.has_attr("rowspan"):
            allowed_attrs["rowspan"] = tag["rowspan"]
        tag.attrs = allowed_attrs

    return str(cloned)


def _render_block_html(tag: Tag, block_type: str) -> str:
    if block_type == "table":
        return _clean_table_html(tag)
    text = _normalize_block_text(tag.get_text("\n", strip=True))
    if not text:
        return ""
    if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        return f"<{tag.name}>{text}</{tag.name}>"
    return f"<p>{text}</p>"


def _render_blocks_html(blocks: list[tuple[str, Tag, str]]) -> str:
    parts = [_render_block_html(tag, block_type) for block_type, tag, _ in blocks]
    return "\n".join(part for part in parts if part)


def _blocks_to_text(blocks: list[tuple[str, Tag, str]]) -> str:
    lines = [text for _, _, text in blocks if text]
    return "\n\n".join(lines)


def _anchor_id(item_key: str) -> str:
    return f"section-{_slugify_item_key(item_key)}"


def build_navigation(document: FilingReaderDocument) -> list[dict[str, str]]:
    return [
        {"anchor_id": section.anchor_id, "title": section.title, "item_key": section.item_key}
        for section in document.sections
    ]


def search_reader_document(
    document: FilingReaderDocument,
    query: str,
) -> list[dict[str, str | int]]:
    if not query.strip():
        return []

    pattern = re.compile(re.escape(query.strip()), re.IGNORECASE)
    matches: list[dict[str, str | int]] = []
    for section in document.sections:
        for match in pattern.finditer(section.content_text):
            matches.append(
                {
                    "anchor_id": section.anchor_id,
                    "section_title": section.title,
                    "offset": match.start(),
                    "match_text": match.group(0),
                }
            )
    return matches


def _build_section_title(item_key: str, remainder: str) -> str:
    remainder = remainder.strip(" .")
    if remainder:
        return f"Item {item_key} {remainder}".strip()
    return f"Item {item_key}"


def _parse_sections_from_html(html: str, filing_type: str | None) -> FilingReaderDocument:
    soup = BeautifulSoup(html, "html.parser")
    FilingTextExtractor._prepare_soup_for_extraction(soup)
    root = soup.body or soup
    blocks = _collect_blocks(root)

    cover_blocks: list[tuple[str, Tag, str]] = []
    section_specs: list[tuple[str, str, str, list[tuple[str, Tag, str]]]] = []
    current_key: str | None = None
    current_title = ""
    current_blocks: list[tuple[str, Tag, str]] = []
    narrative_started = False

    def flush_section() -> None:
        nonlocal current_key, current_title, current_blocks
        if current_key is None:
            return
        section_specs.append((current_key, current_title, _slugify_item_key(current_key), list(current_blocks)))
        current_key = None
        current_title = ""
        current_blocks = []

    for block_type, tag, text in blocks:
        item_match = _is_section_heading(text)
        part_match = _is_part_heading(text)
        signature = _is_signature_heading(text)

        if part_match:
            flush_section()
            narrative_started = True
            part_key = f"PART-{part_match.group(1).upper()}"
            current_key = part_key
            current_title = f"PART {part_match.group(1).upper()}"
            current_blocks = [(block_type, tag, text)]
            continue

        if item_match:
            flush_section()
            narrative_started = True
            item_key = item_match.group(1).upper().replace(" ", "")
            current_key = item_key
            current_title = _build_section_title(item_key, item_match.group(2) or "")
            current_blocks = [(block_type, tag, text)]
            continue

        if signature and narrative_started:
            flush_section()
            current_key = "signature"
            current_title = "Signatures"
            current_blocks = [(block_type, tag, text)]
            continue

        if current_key is None:
            if not narrative_started:
                cover_blocks.append((block_type, tag, text))
            continue

        current_blocks.append((block_type, tag, text))

    flush_section()

    if not section_specs:
        return _parse_sections_from_text(html, filing_type)

    cover_page = None
    if cover_blocks:
        cover_page = FilingCoverPage(
            content_html=_render_blocks_html(cover_blocks),
            content_text=_blocks_to_text(cover_blocks),
        )

    sections = [
        FilingSection(
            item_key=item_key,
            title=title,
            anchor_id=_anchor_id(item_key),
            content_html=_render_blocks_html(content_blocks),
            content_text=_blocks_to_text(content_blocks),
            order=index,
        )
        for index, (item_key, title, _, content_blocks) in enumerate(section_specs, start=1)
    ]

    return FilingReaderDocument(cover_page=cover_page, sections=sections)


def _split_text_sections(text: str, filing_type: str | None) -> FilingReaderDocument:
    trimmed, trim_stats = trim_to_narrative(text, filing_type)
    narrative_offset = int(trim_stats.get("narrative_start_offset") or 0)
    cover_text = text[:narrative_offset].strip() if narrative_offset > 0 else ""

    pattern = re.compile(
        r"(?m)^\s*((?:Item\s+\d+(?:\.\d+)?[A-Z]?)|(?:PART\s+[IVXLC]+))\s*[\.\u2009\u202f]?\s*(.*?)\s*$",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(trimmed))
    if not matches:
        return FilingReaderDocument(
            cover_page=FilingCoverPage(content_html=f"<p>{cover_text}</p>", content_text=cover_text)
            if cover_text
            else None,
            sections=[
                FilingSection(
                    item_key="body",
                    title="Filing Content",
                    anchor_id="section-body",
                    content_html=f"<p>{trimmed.replace(chr(10), '</p><p>')}</p>",
                    content_text=trimmed,
                    order=1,
                )
            ]
            if trimmed
            else [],
        )

    cover_page = (
        FilingCoverPage(content_html=f"<pre>{cover_text}</pre>", content_text=cover_text) if cover_text else None
    )
    sections: list[FilingSection] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(trimmed)
        chunk = trimmed[start:end].strip()
        label = match.group(1).strip()
        if label.upper().startswith("PART"):
            part_key = re.search(r"PART\s+([IVXLC]+)", label, re.IGNORECASE)
            item_key = f"PART-{part_key.group(1).upper()}" if part_key else f"PART-{index}"
            title = label.upper()
        else:
            item_key_match = re.search(r"(\d+(?:\.\d+)?[A-Z]?)", label, re.IGNORECASE)
            item_key = item_key_match.group(1).upper() if item_key_match else str(index)
            title = _build_section_title(item_key, match.group(2) or "")
        sections.append(
            FilingSection(
                item_key=item_key,
                title=title,
                anchor_id=_anchor_id(item_key),
                content_html="".join(f"<p>{line}</p>" for line in chunk.split("\n\n") if line.strip()),
                content_text=chunk,
                order=index + 1,
            )
        )

    return FilingReaderDocument(cover_page=cover_page, sections=sections)


def _parse_sections_from_text(html: str, filing_type: str | None) -> FilingReaderDocument:
    extractor = FilingTextExtractor()
    text, _ = extractor.extract_with_diagnostics(html, filing_type=filing_type)
    return _split_text_sections(text, filing_type)


def parse_filing_reader_document(
    *,
    raw_html: str | None,
    extracted_text: str | None,
    raw_content: str | None,
    filing_type: str | None,
) -> FilingReaderDocument:
    normalized = normalize_filing_narrative_text(
        extracted_text=extracted_text,
        raw_content=raw_content,
        raw_html=raw_html,
        filing_type=filing_type,
    )

    if raw_html:
        try:
            document = _parse_sections_from_html(raw_html, filing_type)
            if document.sections:
                return document
        except Exception as exc:
            logger.warning("filing_section_html_parse_failed", filing_type=filing_type, error=str(exc))

    source = normalized or extracted_text or raw_content or ""
    if raw_html and not source:
        source, _ = FilingTextExtractor().extract_with_diagnostics(raw_html, filing_type=filing_type)

    if not source and raw_html:
        return _parse_sections_from_text(raw_html, filing_type)

    return _split_text_sections(source, filing_type)


def document_has_tables(document: FilingReaderDocument) -> bool:
    return any("<table" in section.content_html.lower() for section in document.sections)
