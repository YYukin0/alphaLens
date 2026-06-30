from sqlalchemy.orm import Session

from app.models.filing_analysis import FilingAnalysis


class FilingAnalysisRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_filing_and_type(self, filing_id: int, analysis_type: str) -> FilingAnalysis | None:
        return (
            self.db.query(FilingAnalysis)
            .filter(
                FilingAnalysis.filing_id == filing_id,
                FilingAnalysis.analysis_type == analysis_type,
            )
            .first()
        )

    def list_by_filing(self, filing_id: int) -> list[FilingAnalysis]:
        return (
            self.db.query(FilingAnalysis)
            .filter(FilingAnalysis.filing_id == filing_id)
            .order_by(FilingAnalysis.analysis_type.asc())
            .all()
        )

    def upsert(
        self,
        filing_id: int,
        analysis_type: str,
        content: str,
        model: str | None,
    ) -> FilingAnalysis:
        existing = self.get_by_filing_and_type(filing_id, analysis_type)
        if existing:
            existing.content = content
            existing.model = model
            self.db.commit()
            self.db.refresh(existing)
            return existing

        row = FilingAnalysis(
            filing_id=filing_id,
            analysis_type=analysis_type,
            content=content,
            model=model,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
