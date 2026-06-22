const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export interface Company {
  id?: number;
  ticker: string;
  company_name: string;
  cik: string;
  in_database?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface FilingSection {
  item_key: string;
  title: string;
  anchor_id: string;
  content_html: string;
  content_text: string;
  order: number;
}

export interface FilingCoverPage {
  content_html: string;
  content_text: string;
}

export interface FilingReader {
  parser_version: number;
  cover_page: FilingCoverPage | null;
  sections: FilingSection[];
}

export interface Filing {
  id: number;
  company_id: number;
  filing_type: string;
  filing_date: string;
  accession_number: string;
  sec_url: string;
  raw_html?: string | null;
  extracted_text?: string | null;
  raw_content?: string | null;
  created_at: string;
}

export interface FilingDetail extends Filing {
  reader?: FilingReader | null;
  company_name?: string | null;
  ticker?: string | null;
}

export interface FilingStats {
  ticker: string;
  total_count: number;
  earliest_filing_date: string | null;
  latest_filing_date: string | null;
  counts_by_type: Record<string, number>;
}

export interface PaginatedFilings {
  items: Filing[];
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  stats: FilingStats;
}

export interface Price {
  id: number;
  company_id: number;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  created_at: string;
}

export interface SyncResponse {
  ticker: string;
  synced_count: number;
  message: string;
  extraction_queued?: number;
}

export interface HistoricalSyncResponse {
  ticker: string;
  discovered_count: number;
  metadata_upserted: number;
  content_synced: number;
  skipped_existing: number;
  extraction_queued: number;
  total_count: number;
  earliest_filing_date: string | null;
  latest_filing_date: string | null;
  counts_by_type: Record<string, number>;
  message: string;
}

export function formatApiError(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (detail && typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    if (typeof record.message === "string") {
      return record.message;
    }
  }
  return "Request failed";
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(formatApiError(error.detail) || `Request failed: ${response.status}`);
  }

  return response.json();
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  searchCompany: (ticker: string) =>
    request<Company>(`/companies/search/${encodeURIComponent(ticker)}`),

  listCompanies: () => request<Company[]>("/companies"),

  localSearchCompanies: (q: string) =>
    request<Company[]>(`/companies/local-search?q=${encodeURIComponent(q)}`),

  syncFilings: (ticker: string, limit = 10) =>
    request<SyncResponse>("/filings/sync", {
      method: "POST",
      body: JSON.stringify({ ticker, limit }),
    }),

  syncHistoricalFilings: (ticker: string, years = 10) =>
    request<HistoricalSyncResponse>("/filings/sync/historical", {
      method: "POST",
      body: JSON.stringify({ ticker, years }),
    }),

  listFilings: (ticker: string, filingType?: string, page = 1, pageSize = 25) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (filingType) {
      params.set("filing_type", filingType);
    }
    return request<PaginatedFilings>(`/filings/${encodeURIComponent(ticker)}?${params.toString()}`);
  },

  getFilingDetail: (filingId: number) =>
    request<FilingDetail>(`/filings/detail/${filingId}`),

  syncPrices: (ticker: string, period = "1y") =>
    request<SyncResponse>("/prices/sync", {
      method: "POST",
      body: JSON.stringify({ ticker, period }),
    }),

  listPrices: (ticker: string) =>
    request<Price[]>(`/prices/${encodeURIComponent(ticker)}`),
};
