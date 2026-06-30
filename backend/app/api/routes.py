from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import (
    get_company_profile_service,
    get_company_service,
    get_event_service,
    get_filing_analysis_service,
    get_filing_service,
    get_financial_data_service,
    get_price_service,
)
from app.exceptions.yahoo_finance import YahooFinanceError
from app.schemas.analysis import (
    CompanyFinancialsResponse,
    CompanyProfileResponse,
    FilingAnalysisBatchResponse,
    FilingAnalysisResponse,
)
from app.schemas.company import CompanyResponse, CompanySearchResponse
from app.schemas.event import EventExtractionResponse, EventResponse
from app.schemas.filing import (
    FilingDetailResponse,
    FilingHistoricalSyncRequest,
    FilingHistoricalSyncResponse,
    FilingReaderResponse,
    FilingResponse,
    FilingSyncRequest,
    FilingSyncResponse,
    PaginatedFilingsResponse,
)
from app.services.filing_section_service import deserialize_reader_document
from app.schemas.price import PriceResponse, PriceSyncRequest, PriceSyncResponse
from app.services.company_profile_service import CompanyProfileService
from app.services.company_service import CompanyService
from app.services.event_service import EventService
from app.services.filing_analysis_service import FilingAnalysisService
from app.services.filing_service import FilingService
from app.services.financial_data_service import FinancialDataService
from app.services.price_service import PriceService

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/companies/search/{ticker}", response_model=CompanySearchResponse)
async def search_company(
    ticker: str,
    company_service: CompanyService = Depends(get_company_service),
) -> CompanySearchResponse:
    try:
        return await company_service.search_ticker(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    company_service: CompanyService = Depends(get_company_service),
) -> list[CompanyResponse]:
    return company_service.list_companies(skip=skip, limit=limit)


@router.get("/companies/local-search", response_model=list[CompanyResponse])
async def local_search_companies(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    company_service: CompanyService = Depends(get_company_service),
) -> list[CompanyResponse]:
    return company_service.search_local(q, limit=limit)


@router.post("/filings/sync", response_model=FilingSyncResponse)
async def sync_filings(
    request: FilingSyncRequest,
    filing_service: FilingService = Depends(get_filing_service),
) -> FilingSyncResponse:
    try:
        result = await filing_service.sync_filings_for_ticker(request.ticker, request.limit)
        return FilingSyncResponse(
            ticker=request.ticker.upper(),
            synced_count=result.synced_count,
            extraction_queued=result.extraction_queued,
            message=(
                f"Synced {result.synced_count} filing(s) for {request.ticker.upper()}. "
                f"Queued {result.extraction_queued} filing(s) for event extraction."
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to sync filings: {exc}") from exc


@router.post("/filings/sync/historical", response_model=FilingHistoricalSyncResponse)
async def sync_historical_filings(
    request: FilingHistoricalSyncRequest,
    filing_service: FilingService = Depends(get_filing_service),
) -> FilingHistoricalSyncResponse:
    try:
        result = await filing_service.sync_historical_filings_for_ticker(
            request.ticker,
            years=request.years,
            download_content=False,
        )

        from app.tasks import sync_historical_filing_content_task

        sync_historical_filing_content_task.delay(request.ticker.upper())

        counts_summary = ", ".join(
            f"{filing_type}: {count}"
            for filing_type, count in sorted(result.counts_by_type.items())
        )
        return FilingHistoricalSyncResponse(
            ticker=request.ticker.upper(),
            discovered_count=result.discovered_count,
            metadata_upserted=result.metadata_upserted,
            content_synced=result.content_synced,
            skipped_existing=result.skipped_existing,
            extraction_queued=result.extraction_queued,
            total_count=result.total_count,
            earliest_filing_date=result.earliest_filing_date,
            latest_filing_date=result.latest_filing_date,
            counts_by_type=result.counts_by_type,
            message=(
                f"Historical backfill indexed {result.discovered_count} filing(s) for "
                f"{request.ticker.upper()} ({counts_summary}). "
                f"Content download queued in background."
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to sync historical filings: {exc}") from exc


@router.get("/filings/{ticker}", response_model=PaginatedFilingsResponse)
async def list_filings(
    ticker: str,
    filing_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    filing_service: FilingService = Depends(get_filing_service),
) -> PaginatedFilingsResponse:
    result = filing_service.list_filings_by_ticker(ticker, filing_type, page, page_size)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No company or filings found for ticker '{ticker.upper()}'. Try syncing filings first.",
        )
    return PaginatedFilingsResponse(
        items=result.items,
        page=result.page,
        page_size=result.page_size,
        total_count=result.total_count,
        total_pages=result.total_pages,
        stats={
            "ticker": result.stats.ticker,
            "total_count": result.stats.total_count,
            "earliest_filing_date": result.stats.earliest_filing_date,
            "latest_filing_date": result.stats.latest_filing_date,
            "counts_by_type": result.stats.counts_by_type,
        },
    )


@router.get("/filings/detail/{filing_id}", response_model=FilingDetailResponse)
async def get_filing_detail(
    filing_id: int,
    filing_service: FilingService = Depends(get_filing_service),
) -> FilingDetailResponse:
    filing = filing_service.get_filing_detail(filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail=f"Filing {filing_id} not found")

    document = deserialize_reader_document(filing.sections_data)
    reader = FilingReaderResponse(**document.to_dict()) if document else None
    response = FilingDetailResponse.model_validate(filing)
    company = filing.company
    return response.model_copy(
        update={
            "reader": reader,
            "company_name": company.company_name if company else None,
            "ticker": company.ticker if company else None,
            "raw_html": None,
            "extracted_text": None if reader else filing.extracted_text,
            "raw_content": None if reader else filing.raw_content,
        }
    )


@router.get("/events/filing/{filing_id}", response_model=list[EventResponse])
async def list_events_by_filing(
    filing_id: int,
    event_service: EventService = Depends(get_event_service),
    filing_service: FilingService = Depends(get_filing_service),
) -> list[EventResponse]:
    filing = filing_service.get_filing_by_id(filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail=f"Filing {filing_id} not found")
    return event_service.list_events_by_filing(filing_id)


@router.get("/events/{ticker}", response_model=list[EventResponse])
async def list_events_by_ticker(
    ticker: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    event_service: EventService = Depends(get_event_service),
    company_service: CompanyService = Depends(get_company_service),
) -> list[EventResponse]:
    company = company_service.get_company_by_ticker(ticker)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{ticker.upper()}' not found")
    return event_service.list_events_by_ticker(company.id, skip, limit)


@router.post("/events/extract/{filing_id}", response_model=EventExtractionResponse)
async def extract_events_for_filing(
    filing_id: int,
    force: bool = Query(False),
    event_service: EventService = Depends(get_event_service),
    filing_service: FilingService = Depends(get_filing_service),
) -> EventExtractionResponse:
    filing = filing_service.get_filing_by_id(filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail=f"Filing {filing_id} not found")
    try:
        count = await event_service.extract_events_for_filing(filing_id, force=force)
        return EventExtractionResponse(
            filing_id=filing_id,
            extracted_count=count,
            message=f"Extracted {count} event(s) from filing {filing_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Event extraction failed: {exc}") from exc


@router.post("/prices/sync", response_model=PriceSyncResponse)
async def sync_prices(
    request: PriceSyncRequest,
    price_service: PriceService = Depends(get_price_service),
) -> PriceSyncResponse:
    try:
        count = await price_service.sync_prices_for_ticker(request.ticker, request.period)
        return PriceSyncResponse(
            ticker=request.ticker.upper(),
            synced_count=count,
            message=f"Successfully synced {count} price record(s) for {request.ticker.upper()}",
        )
    except YahooFinanceError as exc:
        raise HTTPException(status_code=502, detail=exc.to_dict()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/prices/{ticker}", response_model=list[PriceResponse])
async def list_prices(
    ticker: str,
    limit: int = Query(500, ge=1, le=2000),
    price_service: PriceService = Depends(get_price_service),
) -> list[PriceResponse]:
    prices = price_service.list_prices_by_ticker(ticker, limit=limit)
    if not prices:
        company_exists = price_service.company_service.get_company_by_ticker(ticker)
        if not company_exists:
            raise HTTPException(
                status_code=404,
                detail=f"No company or prices found for ticker '{ticker.upper()}'. Try syncing prices first.",
            )
    return prices


@router.get("/companies/{ticker}/profile", response_model=CompanyProfileResponse)
async def get_company_profile(
    ticker: str,
    profile_service: CompanyProfileService = Depends(get_company_profile_service),
) -> CompanyProfileResponse:
    try:
        return await profile_service.get_profile(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/companies/{ticker}/financials", response_model=CompanyFinancialsResponse)
async def get_company_financials(
    ticker: str,
    financial_service: FinancialDataService = Depends(get_financial_data_service),
) -> CompanyFinancialsResponse:
    try:
        return financial_service.fetch_financials(ticker)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch financials: {exc}") from exc


@router.get("/companies/{ticker}/metrics")
async def get_company_metrics(
    ticker: str,
    financial_service: FinancialDataService = Depends(get_financial_data_service),
) -> dict:
    try:
        return financial_service.fetch_key_metrics(ticker)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch metrics: {exc}") from exc


@router.get("/filings/detail/{filing_id}/analysis", response_model=list[FilingAnalysisResponse])
async def list_filing_analyses(
    filing_id: int,
    analysis_service: FilingAnalysisService = Depends(get_filing_analysis_service),
) -> list[FilingAnalysisResponse]:
    filing = analysis_service.get_filing(filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail=f"Filing {filing_id} not found")
    return analysis_service.list_analyses(filing_id)


@router.post("/filings/detail/{filing_id}/analyze", response_model=FilingAnalysisBatchResponse)
async def analyze_filing(
    filing_id: int,
    types: list[str] = Query(default=["summary", "risks", "kpis", "mda"]),
    force: bool = Query(False),
    analysis_service: FilingAnalysisService = Depends(get_filing_analysis_service),
) -> FilingAnalysisBatchResponse:
    try:
        analyses = await analysis_service.analyze_filing(filing_id, types=types, force=force)
        return FilingAnalysisBatchResponse(
            filing_id=filing_id,
            analyses=analyses,
            message=f"Generated {len(analyses)} analysis section(s) for filing {filing_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Filing analysis failed: {exc}") from exc


@router.post("/filings/detail/{filing_id}/compare/{prior_filing_id}")
async def compare_filings(
    filing_id: int,
    prior_filing_id: int,
    analysis_service: FilingAnalysisService = Depends(get_filing_analysis_service),
) -> dict[str, str]:
    try:
        comparison = await analysis_service.compare_with_prior(filing_id, prior_filing_id)
        return {"comparison": comparison}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Filing comparison failed: {exc}") from exc
