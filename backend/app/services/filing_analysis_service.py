from sqlalchemy.orm import Session

from app.config import Settings
from app.models.filing import Filing
from app.repositories.filing_analysis_repository import FilingAnalysisRepository
from app.repositories.filing_repository import FilingRepository
from app.schemas.analysis import ANALYSIS_TYPE_VALUES
from app.services.filing_section_service import deserialize_reader_document
from app.services.openai_filing_analyzer import OpenAIFilingAnalyzer


class FilingAnalysisService:
    SECTIONS_BY_TYPE: dict[str, list[str]] = {
        "summary": [],
        "risks": ["item-1a"],
        "kpis": ["item-2", "item-8"],
        "mda": ["item-7", "item-7a", "item-2"],
    }

    def __init__(
        self,
        db: Session,
        analyzer: OpenAIFilingAnalyzer,
        settings: Settings,
    ) -> None:
        self.db = db
        self.analyzer = analyzer
        self.settings = settings
        self.analysis_repo = FilingAnalysisRepository(db)
        self.filing_repo = FilingRepository(db)

    def get_filing(self, filing_id: int) -> Filing | None:
        return self.filing_repo.get_by_id(filing_id)

    def list_analyses(self, filing_id: int):
        return self.analysis_repo.list_by_filing(filing_id)

    def build_analysis_content(self, filing: Filing, analysis_type: str) -> str:
        document = deserialize_reader_document(filing.sections_data)
        if document and document.sections:
            keys = self.SECTIONS_BY_TYPE.get(analysis_type, [])
            if keys:
                selected = [
                    section.content_text
                    for section in document.sections
                    if section.item_key.lower() in keys
                ]
                if selected:
                    return "\n\n".join(selected)
            return "\n\n".join(section.content_text for section in document.sections[:6])

        text = filing.extracted_text or filing.raw_content or ""
        if not text.strip():
            raise ValueError("No filing content available for analysis")
        return text

    async def analyze_filing(
        self,
        filing_id: int,
        types: list[str] | None = None,
        force: bool = False,
    ) -> list:
        filing = self.get_filing(filing_id)
        if not filing:
            raise ValueError(f"Filing {filing_id} not found")

        requested = types or ["summary", "risks", "kpis", "mda"]
        invalid = [item for item in requested if item not in ANALYSIS_TYPE_VALUES]
        if invalid:
            raise ValueError(f"Invalid analysis types: {', '.join(invalid)}")

        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        results = []
        for analysis_type in requested:
            if not force:
                existing = self.analysis_repo.get_by_filing_and_type(filing_id, analysis_type)
                if existing:
                    results.append(existing)
                    continue

            content = self.build_analysis_content(filing, analysis_type)
            analysis = await self.analyzer.analyze(analysis_type, content, filing.filing_type)
            saved = self.analysis_repo.upsert(
                filing_id=filing_id,
                analysis_type=analysis_type,
                content=analysis,
                model=self.settings.openai_model,
            )
            results.append(saved)

        return results

    async def compare_with_prior(self, filing_id: int, prior_filing_id: int) -> str:
        current = self.get_filing(filing_id)
        prior = self.get_filing(prior_filing_id)
        if not current or not prior:
            raise ValueError("One or both filings not found")
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        current_content = self.build_analysis_content(current, "summary")
        prior_content = self.build_analysis_content(prior, "summary")
        return await self.analyzer.compare_filings(
            current_content,
            prior_content,
            current.filing_type,
            prior.filing_type,
        )
