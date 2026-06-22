from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.repositories.filing_repository import FilingRepository
from app.services.sec_service import SECService

debug_router = APIRouter(tags=["debug"])


def get_sec_service(settings: Settings = Depends(get_settings)) -> SECService:
    return SECService(settings)


@debug_router.get("/yahoo/{ticker}")
async def debug_yahoo_ticker(
    ticker: str,
    period: str = Query(default="1y", pattern=r"^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$"),
) -> dict:
    from app.services.market_data_service import MarketDataService

    service = MarketDataService()
    return service.fetch_debug_snapshot(ticker, period)


@debug_router.get("/filing/{accession_number}")
async def debug_filing_extraction(
    accession_number: str,
    filing_type: str | None = Query(default=None),
    sec_service: SECService = Depends(get_sec_service),
    db: Session = Depends(get_db),
) -> dict:
    """Return filing extraction diagnostics for a specific accession number."""
    repo = FilingRepository(db)
    filing = repo.get_by_accession_number(accession_number)

    if filing and filing.company:
        cik = filing.company.cik
        resolved_filing_type = filing_type or filing.filing_type
        fallback_primary = filing.sec_url.rsplit("/", 1)[-1] if filing.sec_url else None
    else:
        cik_part = accession_number.split("-", 1)[0]
        cik = cik_part.lstrip("0") or "0"
        if not filing_type:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Filing '{accession_number}' not found in database. "
                    "Provide filing_type query parameter to inspect directly from SEC."
                ),
            )
        resolved_filing_type = filing_type
        fallback_primary = None

    _, diagnostics = await sec_service.inspect_primary_filing(
        cik=cik,
        accession_number=accession_number,
        filing_type=resolved_filing_type,
        fallback_primary=fallback_primary,
        raise_on_xbrl=False,
    )

    return diagnostics
