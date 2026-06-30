import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, FileText, Loader2, Sparkles, TrendingUp } from "lucide-react";
import {
  api,
  CompanyFinancials,
  CompanyProfile,
  Filing,
  PaginatedFilings,
} from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FinancialStatementsView } from "@/components/FinancialStatementsView";

export default function CompanyProfilePage() {
  const { ticker = "" } = useParams<{ ticker: string }>();
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [financials, setFinancials] = useState<CompanyFinancials | null>(null);
  const [metrics, setMetrics] = useState<Record<string, number | string>>({});
  const [filings, setFilings] = useState<Filing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"overview" | "financials" | "filings">("overview");

  useEffect(() => {
    if (!ticker) return;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [profileData, financialsData, metricsData] = await Promise.all([
          api.getCompanyProfile(ticker),
          api.getCompanyFinancials(ticker).catch(() => null),
          api.getCompanyMetrics(ticker).catch(() => ({})),
        ]);
        setProfile(profileData);
        setFinancials(financialsData);
        setMetrics(metricsData);

        if (profileData.in_database) {
          const filingPage: PaginatedFilings = await api.listFilings(ticker, undefined, 1, 8);
          setFilings(filingPage.items);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load company profile");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [ticker]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="text-center py-20 space-y-4">
        <p className="text-destructive">{error || "Company not found"}</p>
        <Button asChild variant="outline">
          <Link to="/">Back to Companies</Link>
        </Button>
      </div>
    );
  }

  const metricEntries = Object.entries(metrics).slice(0, 8);

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/">
          <ArrowLeft className="h-4 w-4" />
          Back to Companies
        </Link>
      </Button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-3xl font-bold tracking-tight">{profile.ticker}</h2>
            <Badge variant={profile.in_database ? "default" : "outline"}>
              {profile.in_database ? "Tracked" : "Not Synced"}
            </Badge>
          </div>
          <p className="text-lg text-muted-foreground mt-1">{profile.company_name}</p>
          <p className="text-sm text-muted-foreground mt-1">CIK {profile.cik}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link to={`/filings?ticker=${profile.ticker}`}>
              <FileText className="h-4 w-4" />
              Filings
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link to={`/market?ticker=${profile.ticker}`}>
              <TrendingUp className="h-4 w-4" />
              Chart
            </Link>
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-border pb-2">
        {(["overview", "financials", "filings"] as const).map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => setTab(value)}
            className={`rounded-md px-4 py-2 text-sm font-medium capitalize transition-colors ${
              tab === value
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            }`}
          >
            {value}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Filings</CardDescription>
              <CardTitle className="text-2xl">{profile.filing_count}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Events Extracted</CardDescription>
              <CardTitle className="text-2xl">{profile.event_count}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Latest Filing</CardDescription>
              <CardTitle className="text-lg">
                {profile.latest_filing_type || "—"}
              </CardTitle>
              <CardDescription>
                {profile.latest_filing_date ? formatDate(profile.latest_filing_date) : "No filings synced"}
              </CardDescription>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Filing Mix</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {Object.entries(profile.counts_by_type).map(([type, count]) => (
                <Badge key={type} variant="outline">
                  {type}: {count}
                </Badge>
              ))}
            </CardContent>
          </Card>

          {metricEntries.length > 0 && (
            <Card className="md:col-span-2 xl:col-span-4">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  Key Metrics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {metricEntries.map(([key, value]) => (
                    <div key={key} className="rounded-lg border border-border p-3">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">{key}</p>
                      <p className="text-lg font-semibold mt-1">{formatMetric(value)}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {tab === "financials" && (
        <FinancialStatementsView financials={financials} ticker={profile.ticker} />
      )}

      {tab === "filings" && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Filings</CardTitle>
            <CardDescription>Latest SEC filings indexed for {profile.ticker}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {filings.length === 0 ? (
              <p className="text-muted-foreground text-sm">No filings synced yet.</p>
            ) : (
              filings.map((filing) => (
                <Link
                  key={filing.id}
                  to={`/filings/${filing.id}`}
                  className="flex items-center justify-between rounded-lg border border-border p-4 hover:border-primary/40 hover:bg-secondary/30 transition-colors"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge>{filing.filing_type}</Badge>
                      <span className="text-sm text-muted-foreground">{formatDate(filing.filing_date)}</span>
                    </div>
                    <p className="font-mono text-xs text-muted-foreground mt-1">{filing.accession_number}</p>
                  </div>
                  <span className="text-sm text-primary">Open reader</span>
                </Link>
              ))
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function formatMetric(value: number | string): string {
  if (typeof value === "string") return value;
  if (Math.abs(value) >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (Math.abs(value) <= 1) return `${(value * 100).toFixed(2)}%`;
  return value.toLocaleString();
}
