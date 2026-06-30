from app.services.filing_analysis_service import FilingAnalysisService


def test_build_analysis_content_prefers_risk_section():
    class Section:
        item_key = "item-1a"
        content_text = "Risk factor content"

    class Document:
        sections = [Section()]

    class Filing:
        sections_data = "{}"
        extracted_text = "fallback"
        raw_content = None

    service = FilingAnalysisService.__new__(FilingAnalysisService)
    service.SECTIONS_BY_TYPE = FilingAnalysisService.SECTIONS_BY_TYPE

    from app.services import filing_analysis_service as module

    original = module.deserialize_reader_document
    module.deserialize_reader_document = lambda _: Document()
    try:
        content = service.build_analysis_content(Filing(), "risks")
    finally:
        module.deserialize_reader_document = original

    assert content == "Risk factor content"
