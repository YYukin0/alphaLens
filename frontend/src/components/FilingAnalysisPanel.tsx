import { useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { api, FilingAnalysis } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const TABS = [
  { key: "summary", label: "Summary" },
  { key: "risks", label: "Risks" },
  { key: "kpis", label: "KPIs" },
  { key: "mda", label: "MD&A" },
] as const;

export function FilingAnalysisPanel({ filingId }: { filingId: number }) {
  const [analyses, setAnalyses] = useState<FilingAnalysis[]>([]);
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]["key"]>("summary");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listFilingAnalyses(filingId);
      setAnalyses(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analyses");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [filingId]);

  const handleAnalyze = async (force = false) => {
    setRunning(true);
    setError(null);
    try {
      const result = await api.analyzeFiling(filingId, undefined, force);
      setAnalyses(result.analyses);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setRunning(false);
    }
  };

  const active = analyses.find((item) => item.analysis_type === activeTab);

  return (
    <Card className="border-primary/20 bg-card/50">
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Sparkles className="h-5 w-5 text-primary" />
          AI Research Analysis
        </CardTitle>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => handleAnalyze(false)} disabled={running}>
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : "Analyze"}
          </Button>
          {analyses.length > 0 && (
            <Button size="sm" variant="outline" onClick={() => handleAnalyze(true)} disabled={running}>
              Re-run
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                activeTab === tab.key
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : active ? (
          <div className="prose prose-invert max-w-none text-sm leading-7 whitespace-pre-wrap">
            {active.content}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground py-6 text-center">
            No {activeTab} analysis yet. Click Analyze to generate AI research insights from this filing.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
