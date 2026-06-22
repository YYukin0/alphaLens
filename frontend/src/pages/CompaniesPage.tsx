import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Loader2 } from "lucide-react";
import { api, Company } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function CompaniesPage() {
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const navigate = useNavigate();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const result = await api.searchCompany(ticker.trim());
      setCompany(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setCompany(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncAll = async () => {
    if (!company) return;
    setSyncing(true);
    setError(null);
    try {
      await api.syncFilings(company.ticker);
      await api.syncPrices(company.ticker);
      setCompany({ ...company, in_database: true });
      loadCompanies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const loadCompanies = async () => {
    try {
      const list = await api.listCompanies();
      setCompanies(list);
    } catch {
      // ignore on initial load
    }
  };

  useEffect(() => {
    loadCompanies();
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Companies</h2>
        <p className="text-muted-foreground mt-1">
          Search SEC EDGAR by ticker to find company information
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Search by Ticker</CardTitle>
          <CardDescription>Enter a stock ticker symbol (e.g., AAPL, MSFT, GOOGL)</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex gap-3">
            <Input
              placeholder="Enter ticker..."
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="max-w-xs uppercase"
            />
            <Button type="submit" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Search
            </Button>
          </form>

          {error && (
            <div className="mt-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm">{error}</div>
          )}

          {company && (
            <div className="mt-6 p-4 rounded-lg border border-border bg-secondary/30">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="text-2xl font-bold">{company.ticker}</h3>
                    <Badge variant={company.in_database ? "default" : "outline"}>
                      {company.in_database ? "In Database" : "Not Synced"}
                    </Badge>
                  </div>
                  <p className="text-lg mt-1">{company.company_name}</p>
                  <p className="text-sm text-muted-foreground mt-1">CIK: {company.cik}</p>
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleSyncAll} disabled={syncing}>
                    {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    Sync Data
                  </Button>
                  <Button variant="outline" onClick={() => navigate(`/filings?ticker=${company.ticker}`)}>
                    View Filings
                  </Button>
                  <Button variant="outline" onClick={() => navigate(`/market?ticker=${company.ticker}`)}>
                    View Chart
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {companies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Tracked Companies</CardTitle>
            <CardDescription>Companies already stored in the database</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {companies.map((c) => (
                <button
                  key={c.ticker}
                  onClick={() => {
                    setCompany(c);
                    setTicker(c.ticker);
                  }}
                  className="text-left p-4 rounded-lg border border-border hover:border-primary/50 hover:bg-secondary/50 transition-colors"
                >
                  <div className="font-bold">{c.ticker}</div>
                  <div className="text-sm text-muted-foreground truncate">{c.company_name}</div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
