import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Loader2, RefreshCw, TrendingUp } from "lucide-react";
import { api, Price } from "@/lib/api";
import { formatCurrency, formatDate, formatNumber } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function MarketDataPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTicker = searchParams.get("ticker") || "";
  const [ticker, setTicker] = useState(initialTicker);
  const [prices, setPrices] = useState<Price[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPrices = async (t: string) => {
    if (!t.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.listPrices(t.trim());
      setPrices(data);
      setSearchParams({ ticker: t.trim().toUpperCase() });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load prices");
      setPrices([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialTicker) {
      loadPrices(initialTicker);
    }
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadPrices(ticker);
  };

  const handleSync = async () => {
    if (!ticker.trim()) return;
    setSyncing(true);
    setError(null);
    try {
      await api.syncPrices(ticker.trim(), "1y");
      await loadPrices(ticker);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const chartData = prices.map((p) => ({
    date: p.date,
    close: Number(p.close),
    volume: p.volume,
  }));

  const latestPrice = prices.length > 0 ? prices[prices.length - 1] : null;
  const firstPrice = prices.length > 0 ? prices[0] : null;
  const change =
    latestPrice && firstPrice
      ? ((Number(latestPrice.close) - Number(firstPrice.close)) / Number(firstPrice.close)) * 100
      : null;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Market Data</h2>
        <p className="text-muted-foreground mt-1">Historical price charts from Yahoo Finance</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Price Chart</CardTitle>
          <CardDescription>Enter a ticker to view OHLCV data</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex gap-3 mb-6">
            <Input
              placeholder="Ticker (e.g., AAPL)"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="max-w-xs uppercase"
            />
            <Button type="submit" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <TrendingUp className="h-4 w-4" />}
              Load
            </Button>
            <Button type="button" variant="secondary" onClick={handleSync} disabled={syncing || !ticker.trim()}>
              {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Sync from Yahoo
            </Button>
          </form>

          {error && (
            <div className="mb-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm">{error}</div>
          )}

          {latestPrice && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="p-4 rounded-lg border border-border bg-secondary/30">
                <div className="text-sm text-muted-foreground">Latest Close</div>
                <div className="text-2xl font-bold">{formatCurrency(Number(latestPrice.close))}</div>
              </div>
              <div className="p-4 rounded-lg border border-border bg-secondary/30">
                <div className="text-sm text-muted-foreground">Period Change</div>
                <div className={`text-2xl font-bold ${change && change >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {change !== null ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%` : "—"}
                </div>
              </div>
              <div className="p-4 rounded-lg border border-border bg-secondary/30">
                <div className="text-sm text-muted-foreground">Volume</div>
                <div className="text-2xl font-bold">{formatNumber(latestPrice.volume)}</div>
              </div>
              <div className="p-4 rounded-lg border border-border bg-secondary/30">
                <div className="text-sm text-muted-foreground">Data Points</div>
                <div className="text-2xl font-bold">{prices.length}</div>
              </div>
            </div>
          )}

          {chartData.length > 0 ? (
            <div className="h-[400px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(217, 91%, 60%)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(217, 91%, 60%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(217, 33%, 17%)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "hsl(215, 20%, 65%)", fontSize: 12 }}
                    tickFormatter={(v) => formatDate(v).replace(/, \d{4}/, "")}
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tick={{ fill: "hsl(215, 20%, 65%)", fontSize: 12 }}
                    tickFormatter={(v) => `$${v}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(222, 47%, 8%)",
                      border: "1px solid hsl(217, 33%, 17%)",
                      borderRadius: "8px",
                    }}
                    labelFormatter={(label) => formatDate(String(label))}
                    formatter={(value: number) => [formatCurrency(value), "Close"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="close"
                    stroke="hsl(217, 91%, 60%)"
                    fillOpacity={1}
                    fill="url(#colorClose)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            !loading &&
            ticker && (
              <p className="text-muted-foreground text-center py-8">
                No price data found. Try syncing from Yahoo Finance first.
              </p>
            )
          )}
        </CardContent>
      </Card>
    </div>
  );
}
