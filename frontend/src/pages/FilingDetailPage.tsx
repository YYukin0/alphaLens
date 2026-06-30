import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";
import { api, FilingDetail } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FilingReaderView } from "@/components/FilingReader";
import { FilingAnalysisPanel } from "@/components/FilingAnalysisPanel";
import { SecFilingLink } from "@/components/SecFilingLink";

export default function FilingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [filing, setFiling] = useState<FilingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getFilingDetail(parseInt(id, 10));
        setFiling(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load filing");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !filing) {
    return (
      <div className="text-center py-20">
        <p className="text-destructive mb-4">{error || "Filing not found"}</p>
        <Button asChild variant="outline">
          <Link to="/filings">
            <ArrowLeft className="h-4 w-4" />
            Back to Filings
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/filings">
          <ArrowLeft className="h-4 w-4" />
          Back to Filings
        </Link>
      </Button>

      <Card>
        <CardHeader className="border-b border-border">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-3 mb-2">
                <Badge>{filing.filing_type}</Badge>
                <span className="text-muted-foreground">{formatDate(filing.filing_date)}</span>
                {filing.ticker && (
                  <span className="font-medium">{filing.ticker}</span>
                )}
              </div>
              <CardTitle className="text-2xl">
                {filing.company_name || filing.ticker || "Company"} {filing.filing_type}
              </CardTitle>
              <CardDescription className="font-mono mt-1">{filing.accession_number}</CardDescription>
            </div>
            <SecFilingLink filing={filing} label="View on SEC" className="text-sm" />
          </div>
        </CardHeader>
        <CardContent className="pt-6 space-y-8">
          {filing.reader && filing.reader.sections.length > 0 ? (
            <FilingReaderView reader={filing.reader} filingType={filing.filing_type} />
          ) : filing.extracted_text || filing.raw_content ? (
            <div className="rounded-lg border border-border bg-secondary/20 p-6">
              <p className="text-sm text-muted-foreground mb-4">
                Structured sections are not available yet. Showing extracted text.
              </p>
              <pre className="whitespace-pre-wrap text-sm leading-relaxed font-sans text-foreground/90">
                {(filing.extracted_text || filing.raw_content || "").slice(0, 50000)}
              </pre>
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-8">
              No content available. The filing may not have been fully synced.
            </p>
          )}
          <FilingAnalysisPanel filingId={filing.id} />
        </CardContent>
      </Card>
    </div>
  );
}
