import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  List,
  Search,
  TrendingUp,
  X,
} from "lucide-react";
import type { FilingReader, FilingSection } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

type FilingReaderViewProps = {
  reader: FilingReader;
  filingType?: string;
};

type SearchMatch = {
  anchorId: string;
  sectionTitle: string;
  index: number;
};

type TocGroup = {
  label: string;
  sections: FilingSection[];
};

type SectionHighlight = "risk" | "mda" | "financials" | "earnings" | null;

const IMPORTANT_SECTIONS: Record<string, { highlight: SectionHighlight; label: string }> = {
  "item-1a": { highlight: "risk", label: "Risk Factors" },
  "item-7": { highlight: "mda", label: "MD&A" },
  "item-7a": { highlight: "mda", label: "MD&A" },
  "item-2": { highlight: "financials", label: "Financials" },
  "item-8": { highlight: "financials", label: "Financial Statements" },
  "item-2.02": { highlight: "earnings", label: "Results of Operations" },
  "item-5.02": { highlight: "earnings", label: "Executive Changes" },
};

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function getSectionMeta(section: FilingSection) {
  const key = section.item_key.toLowerCase();
  return IMPORTANT_SECTIONS[key] ?? null;
}

function groupSectionsForToc(sections: FilingSection[]): TocGroup[] {
  const groups: TocGroup[] = [];
  let currentLabel = "Table of Contents";
  let currentSections: FilingSection[] = [];

  const flush = () => {
    if (currentSections.length > 0) {
      groups.push({ label: currentLabel, sections: [...currentSections] });
      currentSections = [];
    }
  };

  for (const section of sections) {
    const key = section.item_key.toLowerCase();
    if (key.startsWith("part-")) {
      flush();
      currentLabel = section.title;
      continue;
    }
    currentSections.push(section);
  }
  flush();

  return groups.length > 0 ? groups : [{ label: "Table of Contents", sections }];
}

function highlightHtml(html: string, query: string, activeIndex: number, matchIndex: number): string {
  if (!query.trim()) {
    return html;
  }
  const pattern = new RegExp(escapeRegExp(query.trim()), "gi");
  let current = 0;
  return html.replace(pattern, (match) => {
    const isActive = current === activeIndex && activeIndex === matchIndex;
    const cssClass = isActive ? "filing-search-hit filing-search-hit-active" : "filing-search-hit";
    current += 1;
    return `<mark class="${cssClass}">${match}</mark>`;
  });
}

function HighlightIcon({ type }: { type: SectionHighlight }) {
  if (type === "risk") return <AlertTriangle className="h-3.5 w-3.5" />;
  if (type === "mda") return <BookOpen className="h-3.5 w-3.5" />;
  if (type === "earnings") return <TrendingUp className="h-3.5 w-3.5" />;
  return null;
}

function SectionContent({
  section,
  collapsed,
  onToggle,
  query,
  activeMatchIndex,
  globalMatchOffset,
}: {
  section: FilingSection;
  collapsed: boolean;
  onToggle: () => void;
  query: string;
  activeMatchIndex: number;
  globalMatchOffset: number;
}) {
  const meta = getSectionMeta(section);
  const html = useMemo(() => {
    if (!query.trim()) {
      return section.content_html;
    }
    return highlightHtml(section.content_html, query, activeMatchIndex, globalMatchOffset);
  }, [section.content_html, query, activeMatchIndex, globalMatchOffset]);

  return (
    <article
      id={section.anchor_id}
      className={cn(
        "scroll-mt-28 rounded-xl border bg-card/40 filing-section-article",
        meta?.highlight === "risk" && "border-amber-500/30 filing-section-risk",
        meta?.highlight === "mda" && "border-blue-500/30 filing-section-mda",
        meta?.highlight === "financials" && "border-emerald-500/30 filing-section-financials",
        meta?.highlight === "earnings" && "border-violet-500/30 filing-section-earnings",
        !meta?.highlight && "border-border",
      )}
    >
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-start justify-between gap-3 px-4 py-4 text-left hover:bg-secondary/20 transition-colors"
      >
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold tracking-tight text-foreground">{section.title}</h2>
            {meta && (
              <Badge
                variant="outline"
                className={cn(
                  "text-[10px] uppercase tracking-wide gap-1",
                  meta.highlight === "risk" && "border-amber-500/50 text-amber-300",
                  meta.highlight === "mda" && "border-blue-500/50 text-blue-300",
                  meta.highlight === "financials" && "border-emerald-500/50 text-emerald-300",
                  meta.highlight === "earnings" && "border-violet-500/50 text-violet-300",
                )}
              >
                <HighlightIcon type={meta.highlight} />
                {meta.label}
              </Badge>
            )}
          </div>
          {!collapsed && (
            <p className="text-xs text-muted-foreground">
              {section.content_text.length.toLocaleString()} characters
            </p>
          )}
        </div>
        {collapsed ? <ChevronRight className="h-5 w-5 shrink-0 mt-0.5" /> : <ChevronDown className="h-5 w-5 shrink-0 mt-0.5" />}
      </button>
      {!collapsed && (
        <div className="border-t border-border/60 px-4 py-6 md:px-8 md:py-8">
          <div
            className="filing-section-content mx-auto max-w-3xl"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        </div>
      )}
    </article>
  );
}

function TableOfContents({
  groups,
  activeAnchor,
  onSelect,
  className,
}: {
  groups: TocGroup[];
  activeAnchor: string | null;
  onSelect: (anchorId: string) => void;
  className?: string;
}) {
  return (
    <nav className={cn("space-y-4", className)}>
      {groups.map((group) => (
        <div key={group.label}>
          <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            {group.label}
          </p>
          <div className="space-y-0.5">
            {group.sections.map((section) => {
              const meta = getSectionMeta(section);
              return (
                <button
                  key={section.anchor_id}
                  type="button"
                  onClick={() => onSelect(section.anchor_id)}
                  className={cn(
                    "w-full rounded-md px-2 py-2 text-left text-sm transition-colors flex items-start gap-2",
                    activeAnchor === section.anchor_id
                      ? "bg-primary/15 text-primary font-medium"
                      : "text-foreground/75 hover:bg-secondary/80 hover:text-foreground",
                  )}
                >
                  {meta && (
                    <span
                      className={cn(
                        "mt-1 h-1.5 w-1.5 shrink-0 rounded-full",
                        meta.highlight === "risk" && "bg-amber-400",
                        meta.highlight === "mda" && "bg-blue-400",
                        meta.highlight === "financials" && "bg-emerald-400",
                        meta.highlight === "earnings" && "bg-violet-400",
                      )}
                    />
                  )}
                  <span className="leading-snug">{section.title}</span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

export function FilingReaderView({ reader, filingType }: FilingReaderViewProps) {
  const [activeAnchor, setActiveAnchor] = useState<string | null>(
    reader.sections[0]?.anchor_id ?? null,
  );
  const [showCoverPage, setShowCoverPage] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [activeMatchIndex, setActiveMatchIndex] = useState(0);
  const [mobileTocOpen, setMobileTocOpen] = useState(false);
  const [readProgress, setReadProgress] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const sections = useMemo(() => reader.sections, [reader.sections]);
  const tocGroups = useMemo(() => groupSectionsForToc(sections), [sections]);

  const searchMatches = useMemo(() => {
    if (!searchQuery.trim()) {
      return [] as SearchMatch[];
    }
    const pattern = new RegExp(escapeRegExp(searchQuery.trim()), "gi");
    const matches: SearchMatch[] = [];
    for (const section of sections) {
      for (const match of section.content_text.matchAll(pattern)) {
        matches.push({
          anchorId: section.anchor_id,
          sectionTitle: section.title,
          index: match.index ?? 0,
        });
      }
    }
    return matches;
  }, [sections, searchQuery]);

  useEffect(() => {
    setActiveMatchIndex(0);
  }, [searchQuery]);

  useEffect(() => {
    const root = containerRef.current;
    if (!root || sections.length === 0) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]?.target.id) {
          setActiveAnchor(visible[0].target.id);
        }
      },
      { root: null, rootMargin: "-15% 0px -60% 0px", threshold: [0.08, 0.25, 0.5] },
    );

    for (const section of sections) {
      const element = root.querySelector(`#${section.anchor_id}`);
      if (element) {
        observer.observe(element);
      }
    }

    return () => observer.disconnect();
  }, [sections]);

  useEffect(() => {
    const onScroll = () => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const total = el.scrollHeight - window.innerHeight;
      if (total <= 0) {
        setReadProgress(100);
        return;
      }
      const scrolled = Math.min(Math.max(-rect.top, 0), total);
      setReadProgress(Math.round((scrolled / total) * 100));
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, [sections]);

  const scrollToSection = (anchorId: string) => {
    setCollapsedSections((current) => ({ ...current, [anchorId]: false }));
    setMobileTocOpen(false);
    requestAnimationFrame(() => {
      const element = containerRef.current?.querySelector(`#${anchorId}`);
      element?.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveAnchor(anchorId);
    });
  };

  const jumpToMatch = (direction: 1 | -1) => {
    if (searchMatches.length === 0) {
      return;
    }
    const nextIndex = (activeMatchIndex + direction + searchMatches.length) % searchMatches.length;
    setActiveMatchIndex(nextIndex);
    scrollToSection(searchMatches[nextIndex].anchorId);
  };

  const expandAll = () => setCollapsedSections({});
  const collapseAll = () => {
    const next: Record<string, boolean> = {};
    for (const section of sections) {
      next[section.anchor_id] = true;
    }
    setCollapsedSections(next);
  };

  const matchOffsets = useMemo(() => {
    const offsets: Record<string, number> = {};
    let running = 0;
    for (const section of sections) {
      offsets[section.anchor_id] = running;
      if (!searchQuery.trim()) {
        continue;
      }
      const pattern = new RegExp(escapeRegExp(searchQuery.trim()), "gi");
      running += [...section.content_text.matchAll(pattern)].length;
    }
    return offsets;
  }, [sections, searchQuery]);

  if (sections.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        No readable sections were parsed for this filing.
      </p>
    );
  }

  const activeMatch = searchMatches[activeMatchIndex];
  const importantCount = sections.filter((s) => getSectionMeta(s)).length;

  return (
    <div className="space-y-4">
      <div
        className="fixed top-[73px] left-0 right-0 z-40 h-0.5 bg-border/40"
        aria-hidden
      >
        <div
          className="h-full bg-primary transition-[width] duration-150"
          style={{ width: `${readProgress}%` }}
        />
      </div>

      <div className="sticky top-[74px] z-30 -mx-2 rounded-xl border border-border bg-card/95 p-3 backdrop-blur-md shadow-sm space-y-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search this filing..."
              className="pl-9"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground min-w-[72px] text-center">
              {searchMatches.length > 0
                ? `${activeMatchIndex + 1} / ${searchMatches.length}`
                : searchQuery
                  ? "0 matches"
                  : ""}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={searchMatches.length === 0}
              onClick={() => jumpToMatch(-1)}
            >
              <ChevronUp className="h-4 w-4" />
              <span className="hidden sm:inline">Prev</span>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={searchMatches.length === 0}
              onClick={() => jumpToMatch(1)}
            >
              <span className="hidden sm:inline">Next</span>
              <ChevronDown className="h-4 w-4" />
            </Button>
            <Button type="button" variant="outline" size="sm" className="lg:hidden" onClick={() => setMobileTocOpen(true)}>
              <List className="h-4 w-4" />
              Contents
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
          <span>
            {sections.length} sections
            {filingType ? ` · ${filingType}` : ""}
            {importantCount > 0 ? ` · ${importantCount} key sections` : ""}
          </span>
          <div className="flex gap-2">
            <button type="button" className="hover:text-foreground underline-offset-2 hover:underline" onClick={expandAll}>
              Expand all
            </button>
            <span>·</span>
            <button type="button" className="hover:text-foreground underline-offset-2 hover:underline" onClick={collapseAll}>
              Collapse all
            </button>
          </div>
        </div>
      </div>

      {activeMatch && (
        <p className="text-xs text-muted-foreground px-1">
          Match in {activeMatch.sectionTitle}
        </p>
      )}

      {mobileTocOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            aria-label="Close table of contents"
            onClick={() => setMobileTocOpen(false)}
          />
          <div className="absolute bottom-0 left-0 right-0 max-h-[75vh] overflow-y-auto rounded-t-2xl border border-border bg-card p-4 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-semibold">Table of Contents</h3>
              <Button type="button" variant="ghost" size="sm" onClick={() => setMobileTocOpen(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <TableOfContents groups={tocGroups} activeAnchor={activeAnchor} onSelect={scrollToSection} />
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="hidden lg:block lg:sticky lg:top-44 lg:self-start lg:max-h-[calc(100vh-12rem)]">
          <div className="rounded-xl border border-border bg-card/60 p-3 overflow-y-auto max-h-[calc(100vh-12rem)]">
            <p className="px-2 pb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Table of Contents
            </p>
            <TableOfContents groups={tocGroups} activeAnchor={activeAnchor} onSelect={scrollToSection} />
          </div>
        </aside>

        <div ref={containerRef} className="space-y-5 min-w-0 pb-16">
          {reader.cover_page && (
            <div className="rounded-xl border border-border bg-secondary/10">
              <button
                type="button"
                onClick={() => setShowCoverPage((value) => !value)}
                className="flex w-full items-center gap-2 px-4 py-3 text-sm font-medium text-left hover:bg-secondary/30"
              >
                {showCoverPage ? (
                  <ChevronDown className="h-4 w-4 shrink-0" />
                ) : (
                  <ChevronRight className="h-4 w-4 shrink-0" />
                )}
                SEC Cover Page
              </button>
              {showCoverPage && (
                <div className="border-t border-border px-4 py-6 md:px-8">
                  <div
                    className="filing-cover-content mx-auto max-w-3xl"
                    dangerouslySetInnerHTML={{ __html: reader.cover_page.content_html }}
                  />
                </div>
              )}
            </div>
          )}

          {sections.map((section) => (
            <SectionContent
              key={section.anchor_id}
              section={section}
              collapsed={Boolean(collapsedSections[section.anchor_id])}
              onToggle={() =>
                setCollapsedSections((current) => ({
                  ...current,
                  [section.anchor_id]: !current[section.anchor_id],
                }))
              }
              query={searchQuery}
              activeMatchIndex={activeMatchIndex}
              globalMatchOffset={matchOffsets[section.anchor_id] ?? 0}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
