import json
from datetime import date

from app.models.company import Company
from app.models.filing import Filing
from app.services.filing_section_service import (
    build_navigation,
    parse_filing_reader_document,
    search_reader_document,
    serialize_reader_document,
)


def _sample_reader_payload() -> str:
    document = parse_filing_reader_document(
        raw_html=None,
        extracted_text=(
            "UNITED STATES\nFORM 8-K\n\n"
            "Item 2.02 Results of Operations and Financial Condition.\n\n"
            "Apple issued a press release.\n\n"
            "Item 9.01 Financial Statements and Exhibits.\n\n"
            "Exhibit 99.1 attached.\n"
        ),
        raw_content=None,
        filing_type="8-K",
    )
    return serialize_reader_document(document)


def test_build_navigation(client, db_session):
    company = Company(ticker="AAPL", company_name="Apple Inc.", cik="320193")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    filing = Filing(
        company_id=company.id,
        filing_type="8-K",
        filing_date=date(2026, 4, 30),
        accession_number="0000320193-26-000011",
        sec_url="https://www.sec.gov/example.htm",
        extracted_text="Item 2.02 Results\n\nItem 9.01 Financial Statements",
        sections_data=_sample_reader_payload(),
    )
    db_session.add(filing)
    db_session.commit()
    db_session.refresh(filing)

    response = client.get(f"/api/v1/filings/detail/{filing.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["company_name"] == "Apple Inc."
    assert body["ticker"] == "AAPL"
    assert body["reader"] is not None
    assert len(body["reader"]["sections"]) >= 2
    assert body["raw_html"] is None
    assert body["extracted_text"] is None
    assert body["reader"]["sections"][0]["title"].startswith("Item")


def test_filing_detail_not_found(client):
    response = client.get("/api/v1/filings/detail/999999")
    assert response.status_code == 404


def test_pagination_defaults(client, db_session):
    company = Company(ticker="AAPL", company_name="Apple Inc.", cik="320193")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    for index in range(30):
        db_session.add(
            Filing(
                company_id=company.id,
                filing_type="8-K",
                filing_date=date(2026, 1, 1),
                accession_number=f"0000320193-26-{index:06d}",
                sec_url=f"https://www.sec.gov/{index}.htm",
            )
        )
    db_session.commit()

    response = client.get("/api/v1/filings/AAPL?page=1&page_size=25")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 25
    assert body["total_count"] == 30
    assert body["total_pages"] == 2
    assert len(body["items"]) == 25


def test_search_reader_document():
    document = parse_filing_reader_document(
        raw_html=None,
        extracted_text=(
            "Item 2.02 Results of Operations and Financial Condition.\n\n"
            "Apple issued a press release.\n\n"
            "Item 9.01 Financial Statements and Exhibits.\n"
        ),
        raw_content=None,
        filing_type="8-K",
    )
    matches = search_reader_document(document, "press release")
    assert len(matches) == 1
    assert matches[0]["section_title"].startswith("Item 2.02")


def test_build_navigation_items():
    document = parse_filing_reader_document(
        raw_html=(__import__("pathlib").Path(__file__).parent / "fixtures" / "goog_10q_primary.html").read_text(),
        extracted_text=None,
        raw_content=None,
        filing_type="10-Q",
    )
    navigation = build_navigation(document)
    titles = [item["title"] for item in navigation]
    assert any("PART I" in title for title in titles)
    assert any("Item 1" in title for title in titles)
    assert any("Item 2" in title for title in titles)
