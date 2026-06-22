# AlphaLens

AI-powered equity research platform for ingesting SEC filings and market data, with a research dashboard and structured filing reader.

AlphaLens pulls 8-K, 10-Q, and 10-K filings from EDGAR, extracts readable narrative text, parses filings into navigable sections with preserved financial tables, and stores OHLCV price history from Yahoo Finance.

---

## Features

### SEC filing ingestion

- Sync recent filings or run a **10-year historical backfill** per ticker
- Primary HTML document selection (excludes XBRL attachments and inline XBRL renderer pages)
- Inline XBRL cleanup: hidden metadata removed, cover-page boilerplate trimmed
- Paginated filing history with per-type counts and date ranges

### Filing reader

- Structured sections by Item (10-K, 10-Q, 8-K) and Part (10-Q/10-K)
- Sticky section navigation with scroll-to-section and active highlighting
- SEC cover page collapsed by default (`Show Cover Page` toggle)
- Financial tables preserved as HTML (not flattened to plain text)
- In-filing keyword search with match highlighting and prev/next navigation
- Collapsible sections

### Market data

- Yahoo Finance OHLCV sync and charting in the dashboard

### Event extraction (optional)

- LLM-based corporate event extraction from filing text (requires `OPENAI_API_KEY`)
- Background processing via Celery

---

## Architecture

```
AlphaLens/
├── backend/          # FastAPI, SQLAlchemy, Alembic, Celery
├── frontend/         # React, Vite, TailwindCSS, Recharts
├── docker/           # PostgreSQL init scripts
└── docker-compose.yml
```

| Service | Role |
|---------|------|
| `backend` | REST API, filing extraction, section parsing |
| `celery-worker` | Background historical content sync, event extraction |
| `postgres` | Persistent storage |
| `redis` | Celery broker |
| `frontend` | Research dashboard |

### Backend layers

| Layer | Purpose |
|-------|---------|
| `api/` | HTTP routes |
| `services/` | SEC, filings, sections, Yahoo Finance, events |
| `repositories/` | Database access |
| `models/` | SQLAlchemy ORM |
| `schemas/` | Pydantic request/response models |

Key services:

- `sec_service.py` — EDGAR submissions, archive files, HTML download
- `filing_document_service.py` — HTML extraction, XBRL filtering, narrative trimming
- `filing_section_service.py` — Section parser, table preservation, search helpers
- `filing_service.py` — Sync orchestration, pagination, reader assembly

---

## Quick start (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Ports **5173**, **8000**, **5432**, and **6379** available

### Start

```bash
docker compose up --build
```

First run takes about 1–2 minutes while migrations run and containers become healthy.

### Access

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/v1/health |
| PostgreSQL | `localhost:5432` — user `alphalens`, password `alphalens`, db `alphalens` |

### Stop

```bash
docker compose down
```

Reset database:

```bash
docker compose down -v
```

---

## Usage

1. Open http://localhost:5173
2. **Companies** — search a ticker (e.g. `AAPL`, `GOOG`, `MSFT`) and sync data
3. **Filings**
   - Enter a ticker and click **Load**
   - **Sync from SEC** — fetch recent filing metadata and content
   - **Full Historical Sync** — index up to 10 years of 8-K / 10-Q / 10-K filings; content downloads in the background via Celery
   - Filter by type; paginate with Previous / Next
4. **View** a filing to open the structured reader:
   - Section sidebar (Item 1, Item 7, Item 2.02, etc.)
   - Search within the filing
   - Financial tables rendered as HTML
5. **Market Data** — sync and chart 1-year OHLCV history

### Recommended first sync

```
Companies → search AAPL → Sync Data
Filings → AAPL → Full Historical Sync → wait for Celery backfill → open any filing
```

---

## API reference

Base URL: `http://localhost:8000/api/v1`

### Health & companies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/companies/search/{ticker}` | Lookup ticker via SEC EDGAR |
| GET | `/companies` | List tracked companies |
| GET | `/companies/local-search?q=` | Search companies already in the database |

### Filings

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/filings/sync` | Sync recent filings (`{"ticker": "AAPL", "limit": 10}`) |
| POST | `/filings/sync/historical` | Index historical filings (`{"ticker": "AAPL", "years": 10}`) |
| GET | `/filings/{ticker}` | Paginated list — `?page=1&page_size=25&filing_type=10-K` |
| GET | `/filings/detail/{id}` | Filing detail with structured `reader` payload |

**Filing detail response** includes:

- Filing metadata (type, date, accession, company name, ticker)
- `reader.cover_page` — SEC boilerplate (hidden in UI by default)
- `reader.sections[]` — `item_key`, `title`, `anchor_id`, `content_html`, `content_text`

### Prices

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/prices/sync` | Sync Yahoo Finance OHLCV (`{"ticker": "AAPL", "period": "1y"}`) |
| GET | `/prices/{ticker}` | List stored price records |

### Events (requires OpenAI)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/events/{ticker}` | List extracted events for a company |
| GET | `/events/filing/{filing_id}` | List events for one filing |
| POST | `/events/extract/{filing_id}` | Trigger extraction (`?force=true` to re-run) |

### Debug

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/debug/yahoo/{ticker}` | Yahoo Finance probe snapshot |
| GET | `/debug/filing/{accession}?filing_type=8-K` | Extraction diagnostics for an accession |

---

## Filing reader

The reader transforms raw SEC HTML into a navigable research view similar to BamSEC or Quartr.

**Parsing pipeline**

1. Download primary HTML from EDGAR index
2. Remove inline XBRL hidden blocks and metadata tags
3. Trim SEC cover-page boilerplate before first Item / Part
4. Split into sections at Item headings (and Part I / Part II for 10-Q/10-K)
5. Preserve `<table>` elements as styled HTML inside each section
6. Store parsed sections in `filings.sections_data` (JSON)

**Supported section types**

| Filing | Examples |
|--------|----------|
| 10-K | Item 1, 1A, 7, 8, … |
| 10-Q | Part I, Item 1, 2, 3, 4, Part II |
| 8-K | Item 2.02, 5.02, 9.01, … |

Sections are parsed lazily on first detail view if not already stored.

---

## Local development

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Requires PostgreSQL and Redis running locally
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL=http://localhost:8000/api/v1` in `frontend/.env.local` if needed.

### Tests

```bash
# Via Docker (recommended)
docker compose run --rm backend pytest -v

# Or locally from backend/
pytest -v
```

---

## Database schema

| Table | Key fields |
|-------|------------|
| `companies` | ticker, company_name, cik |
| `filings` | company_id, filing_type, filing_date, accession_number, sec_url, raw_html, extracted_text, sections_data |
| `prices` | company_id, date, open, high, low, close, volume |
| `events` | filing_id, event_type, title, summary, event_date |

Migrations run automatically on backend startup (`alembic upgrade head`).

| Migration | Adds |
|-----------|------|
| `001_initial` | companies, filings, prices |
| `002_events` | events table |
| `003_filing_html` | raw_html, extracted_text |
| `004_filing_sections` | sections_data (parsed reader JSON) |

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://alphalens:alphalens@postgres:5432/alphalens` | PostgreSQL connection |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker |
| `SEC_USER_AGENT` | `AlphaLens Research Platform contact@alphalens.local` | Required by SEC EDGAR — **set a real contact email for production** |
| `OPENAI_API_KEY` | — | Enables LLM event extraction |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for event extraction |
| `AUTO_EXTRACT_EVENTS` | `true` | Queue event extraction after filing sync |
| `DEBUG` | `false` | Verbose logging |

Copy `.env.example` to `.env` in the project root for Docker Compose overrides.

---

## Roadmap

| Phase | Status | Scope |
|-------|--------|-------|
| **Phase 1** | Done | SEC sync, Yahoo prices, dashboard |
| **Phase 2** | Done | Historical filing sync, XBRL-safe extraction, LLM event extraction |
| **Phase 3** | Done | Structured filing reader, section nav, table preservation, in-filing search |
| Phase 4 | Planned | Form 4, 13F, earnings transcripts |
| Phase 5 | Planned | Event-driven backtesting |
| Phase 6 | Planned | Research assistant (natural-language interface) |

---

## License

MIT
