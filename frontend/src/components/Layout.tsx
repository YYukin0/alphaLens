import { Link, useLocation } from "react-router-dom";
import { BarChart3, Building2, FileText, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Companies", icon: Building2 },
  { to: "/filings", label: "Filings", icon: FileText },
  { to: "/market", label: "Market Data", icon: TrendingUp },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <BarChart3 className="h-7 w-7 text-primary" />
            <div>
              <h1 className="text-xl font-bold tracking-tight">DeepEquity</h1>
              <p className="text-xs text-muted-foreground">AI Equity Research</p>
            </div>
          </Link>
          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
                  location.pathname === to || (to !== "/" && location.pathname.startsWith(to))
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">{children}</main>
    </div>
  );
}
