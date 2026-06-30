import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { scrollToSection, useActiveSection } from "./useActiveSection";

const NAV_ITEMS = [
  { id: "what-is", label: "Product" },
  { id: "features", label: "Features" },
  { id: "preview", label: "Preview" },
  { id: "how-it-works", label: "Workflow" },
  { id: "why-ai", label: "Why AI" },
];

export function LandingNav() {
  const active = useActiveSection(NAV_ITEMS.map((item) => item.id));

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-white/[0.06] bg-[#05070a]/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <button
          type="button"
          onClick={() => scrollToSection("hero")}
          className="flex items-center gap-2 text-left"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand/15 ring-1 ring-brand/30">
            <span className="text-sm font-bold text-brand">D</span>
          </div>
          <span className="text-sm font-semibold tracking-tight text-white">DeepEquity</span>
        </button>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => scrollToSection(item.id)}
              className={cn(
                "rounded-full px-3 py-1.5 text-sm transition-colors",
                active === item.id
                  ? "bg-white/10 text-white"
                  : "text-white/55 hover:text-white/90",
              )}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            to="/companies"
            className="hidden rounded-full px-4 py-2 text-sm text-white/70 transition-colors hover:text-white sm:inline-flex"
          >
            Sign in
          </Link>
          <Link
            to="/companies"
            className="inline-flex items-center gap-2 rounded-full bg-brand px-4 py-2 text-sm font-medium text-[#04120c] transition-transform hover:scale-[1.02]"
          >
            Explore Platform
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </header>
  );
}
