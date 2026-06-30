import type { CompanyFinancials } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const LABELS: Record<string, string> = {
  income_statement: "Income Statement",
  balance_sheet: "Balance Sheet",
  cash_flow: "Cash Flow Statement",
};

export function FinancialStatementsView({
  financials,
  ticker,
}: {
  financials: CompanyFinancials | null;
  ticker: string;
}) {
  if (!financials || financials.statements.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-muted-foreground">
          Financial statements are not available for {ticker} right now.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {financials.currency && (
        <p className="text-sm text-muted-foreground">Currency: {financials.currency}</p>
      )}
      {financials.statements.map((statement) => (
        <Card key={statement.statement_type}>
          <CardHeader>
            <CardTitle>{LABELS[statement.statement_type] || statement.statement_type}</CardTitle>
            <CardDescription>Source: Yahoo Finance</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="filing-table min-w-full">
              <thead>
                <tr>
                  {statement.columns.map((column) => (
                    <th key={column}>{column === "line_item" ? "Line Item" : column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {statement.rows.map((row, index) => (
                  <tr key={`${statement.statement_type}-${index}`}>
                    {statement.columns.map((column) => (
                      <td key={column} className={column === "line_item" ? "font-medium" : "text-right font-mono text-xs"}>
                        {row[column] ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
