import type { Filing } from "@/lib/api";
import { cn } from "@/lib/utils";

const recentOpens = new Map<string, number>();
const OPEN_COOLDOWN_MS = 1000;

function shouldAllowOpen(accessionNumber: string): boolean {
  const now = Date.now();
  const lastOpenedAt = recentOpens.get(accessionNumber) ?? 0;
  if (now - lastOpenedAt < OPEN_COOLDOWN_MS) {
    return false;
  }
  recentOpens.set(accessionNumber, now);
  return true;
}

type SecFilingLinkProps = {
  filing: Pick<Filing, "accession_number" | "sec_url">;
  label?: string;
  className?: string;
};

export function SecFilingLink({ filing, label = "SEC", className }: SecFilingLinkProps) {
  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (!shouldAllowOpen(filing.accession_number)) {
      return;
    }
    window.open(filing.sec_url, "_blank", "noopener,noreferrer");
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        "inline-flex items-center gap-1 text-primary hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm",
        className,
      )}
    >
      {label}
    </button>
  );
}
