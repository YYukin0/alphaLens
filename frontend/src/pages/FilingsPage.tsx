import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { FileText, History, Loader2, RefreshCw } from "lucide-react";
import { api, Filing, FilingStats } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SecFilingLink } from "@/components/SecFilingLink";

const FILING_TYPES = ["All", "8-K", "10-Q", "10-K"];
const PAGE_SIZE = 25;

export default function FilingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialTicker = searchParams.get("ticker") || "";
  const initialPage = Number(searchParams.get("page") || "1");

  const [ticker, setTicker] = useState(initialTicker);
  const [filingType, setFilingType] = useState("All");
  const [filings, setFilings] = useState<Filing[]>([]);
  const [stats, setStats] = useState<FilingStats | null>(null);
  const [page, setPage] = useState(initialPage > 0 ? initialPage : 1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [historicalSyncing, setHistoricalSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadFilings = async (t: string, type?: string, pageNumber = 1) => {
    if (!t.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const typeFilter = type && type !== "All" ? type : undefined;
      const pageSize = PAGE_SIZE;
      const data = await api.listFilings(t.trim(), typeFilter, pageNumber, pageSize);
      setFilings(data.items);
      setStats(data.stats);
      setPage(data.page);
      setTotalPages(data.total_pages);
      setTotalCount(data.total_count);
      setSearchParams({
        ticker: t.trim().toUpperCase(),
        page: String(data.page),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load filings");
      setFilings([]);
      setStats(null);
      setTotalPages(0);
      setTotalCount(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialTicker) {
      loadFilings(initialTicker, filingType, initialPage > 0 ? initialPage : 1);
    }
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadFilings(ticker, filingType, 1);
  };

  const handleSync = async () => {
    if (!ticker.trim()) return;
    setSyncing(true);
    setError(null);
    setSyncMessage(null);
    try {
      const result = await api.syncFilings(ticker.trim());
      setSyncMessage(result.message);
      await loadFilings(ticker, filingType, 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const handleHistoricalSync = async () => {
    if (!ticker.trim()) return;
    setHistoricalSyncing(true);
    setError(null);
    setSyncMessage(null);
    try {
      const result = await api.syncHistoricalFilings(ticker.trim());
      setSyncMessage(result.message);
      await loadFilings(ticker, filingType, 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Historical sync failed");
    } finally {
      setHistoricalSyncing(false);
    }
  };

  const handleTypeFilter = (type: string) => {
    setFilingType(type);
    setPage(1);
    if (ticker.trim()) {
      loadFilings(ticker, type, 1);
    }
  };

  const handlePageChange = (nextPage: number) => {
    if (nextPage < 1 || (totalPages > 0 && nextPage > totalPages)) return;
    setPage(nextPage);
    loadFilings(ticker, filingType, nextPage);
  };

  const handleViewFiling = (filing: Filing) => (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    navigate(`/filings/${filing.id}`);
  };

  const formatTypeCounts = (counts: Record<string, number>) =>
    ["10-K", "10-Q", "8-K"]
      .filter((type) => counts[type])
      .map((type) => `${type}: ${counts[type]}`)
      .join(" · ");

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Filings</h2>
        <p className="text-muted-foreground mt-1">View SEC filing history (8-K, 10-Q, 10-K)</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filing History</CardTitle>
          <CardDescription>Search filings by ticker symbol</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex flex-wrap gap-3 mb-4">
            <Input
              placeholder="Ticker (e.g., AAPL)"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="max-w-xs uppercase"
            />
            <Button type="submit" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
              Load
            </Button>
            <Button type="button" variant="secondary" onClick={handleSync} disabled={syncing || !ticker.trim()}>
              {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Sync from SEC
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleHistoricalSync}
              disabled={historicalSyncing || !ticker.trim()}
            >
              {historicalSyncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <History className="h-4 w-4" />}
              Full Historical Sync
            </Button>
          </form>

          <div className="flex gap-2 mb-4">
            {FILING_TYPES.map((type) => (
              <Button
                key={type}
                variant={filingType === type ? "default" : "outline"}
                size="sm"
                onClick={() => handleTypeFilter(type)}
              >
                {type}
              </Button>
            ))}
          </div>

          {stats && (
            <div className="mb-4 rounded-lg border border-border bg-secondary/20 p-4 text-sm space-y-1">
              <p>
                <span className="font-medium">{stats.total_count}</span> total filings
                {stats.earliest_filing_date && stats.latest_filing_date && (
                  <>
                    {" "}
                    · {formatDate(stats.earliest_filing_date)} to {formatDate(stats.latest_filing_date)}
                  </>
                )}
              </p>
              <p className="text-muted-foreground">{formatTypeCounts(stats.counts_by_type)}</p>
            </div>
          )}

          {syncMessage && (
            <div className="mb-4 p-3 rounded-md bg-primary/10 text-primary text-sm">{syncMessage}</div>
          )}

          {error && (
            <div className="mb-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm">{error}</div>
          )}

          {filings.length > 0 ? (
            <>
              <div className="rounded-lg border border-border overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-secondary/50">
                    <tr>
                      <th className="text-left p-3 font-medium">Type</th>
                      <th className="text-left p-3 font-medium">Date</th>
                      <th className="text-left p-3 font-medium">Accession #</th>
                      <th className="text-left p-3 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filings.map((filing) => (
                      <tr
                        key={`${filing.id}-${filing.accession_number}`}
                        className="border-t border-border hover:bg-secondary/30"
                      >
                        <td className="p-3">
                          <Badge variant="secondary">{filing.filing_type}</Badge>
                        </td>
                        <td className="p-3">{formatDate(filing.filing_date)}</td>
                        <td className="p-3 font-mono text-xs text-muted-foreground">{filing.accession_number}</td>
                        <td className="p-3">
                          <Button type="button" variant="ghost" size="sm" onClick={handleViewFiling(filing)}>
                            View
                          </Button>
                          <SecFilingLink filing={filing} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center justify-between mt-4 text-sm">
                <p className="text-muted-foreground">
                  Page {page} of {Math.max(totalPages, 1)} · {totalCount} filings
                </p>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={page <= 1 || loading}
                    onClick={() => handlePageChange(page - 1)}
                  >
                    Previous
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={totalPages === 0 || page >= totalPages || loading}
                    onClick={() => handlePageChange(page + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          ) : (
            !loading &&
            ticker && (
              <p className="text-muted-foreground text-center py-8">
                No filings found. Try syncing from SEC first.
              </p>
            )
          )}
        </CardContent>
      </Card>
    </div>
  );
}
