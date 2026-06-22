import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronRight, ChevronUp, Search } from "lucide-react";
import type { FilingCoverPage, FilingReader, FilingSection } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type FilingReaderViewProps = {
  reader: FilingReader;
};

type SearchMatch = {
  anchorId: string;
  sectionTitle: string;
  index: number;
};

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
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
  const html = useMemo(() => {
    if (!query.trim()) {
      return section.content_html;
    }
    return highlightHtml(section.content_html, query, activeMatchIndex, globalMatchOffset);
  }, [section.content_html, query, activeMatchIndex, globalMatchOffset]);

  return (
    <article id={section.anchor_id} className="scroll-mt-24 rounded-lg border border-border bg-card/30">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-secondary/30"
      >
        <h2 className="text-lg font-semibold tracking-tight">{section.title}</h2>
        {collapsed ? <ChevronRight className="h-4 w-4 shrink-0" /> : <ChevronDown className="h-4 w-4 shrink-0" />}
      </button>
      {!collapsed && (
        <div className="border-t border-border px-4 py-4">
          <div
            className="filing-section-content space-y-4 text-[15px] leading-7 text-foreground/90"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        </div>
      )}
    </article>
  );
}

export function FilingReaderView({ reader }: FilingReaderViewProps) {
  const [activeAnchor, setActiveAnchor] = useState<string | null>(
    reader.sections[0]?.anchor_id ?? null,
  );
  const [showCoverPage, setShowCoverPage] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [activeMatchIndex, setActiveMatchIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const sections = useMemo(() => reader.sections, [reader.sections]);

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
      { root: null, rootMargin: "-20% 0px -55% 0px", threshold: [0.1, 0.35, 0.6] },
    );

    for (const section of sections) {
      const element = root.querySelector(`#${section.anchor_id}`);
      if (element) {
        observer.observe(element);
      }
    }

    return () => observer.disconnect();
  }, [sections]);

  const scrollToSection = (anchorId: string) => {
    setCollapsedSections((current) => ({ ...current, [anchorId]: false }));
    const element = containerRef.current?.querySelector(`#${anchorId}`);
    element?.scrollIntoView({ behavior: "smooth", block: "start" });
    setActiveAnchor(anchorId);
  };

  const jumpToMatch = (direction: 1 | -1) => {
    if (searchMatches.length === 0) {
      return;
    }
    const nextIndex = (activeMatchIndex + direction + searchMatches.length) % searchMatches.length;
    setActiveMatchIndex(nextIndex);
    scrollToSection(searchMatches[nextIndex].anchorId);
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

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-lg border border-border bg-card/60 p-3 md:flex-row md:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search inside filing..."
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground min-w-[88px] text-center">
            {searchMatches.length > 0
              ? `${activeMatchIndex + 1} / ${searchMatches.length}`
              : searchQuery
                ? "0 matches"
                : ""}
          </span>
          <Button type="button" variant="outline" size="sm" disabled={searchMatches.length === 0} onClick={() => jumpToMatch(-1)}>
            <ChevronUp className="h-4 w-4" />
            Prev
          </Button>
          <Button type="button" variant="outline" size="sm" disabled={searchMatches.length === 0} onClick={() => jumpToMatch(1)}>
            Next
            <ChevronDown className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {activeMatch && (
        <p className="text-xs text-muted-foreground px-1">
          Match in {activeMatch.sectionTitle}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <div className="rounded-lg border border-border bg-card/60 p-3">
            <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Sections
            </p>
            <nav className="max-h-[70vh] overflow-y-auto space-y-1">
              {sections.map((section) => (
                <button
                  key={section.anchor_id}
                  type="button"
                  onClick={() => scrollToSection(section.anchor_id)}
                  className={cn(
                    "w-full rounded-md px-2 py-2 text-left text-sm transition-colors",
                    activeAnchor === section.anchor_id
                      ? "bg-primary/15 text-primary"
                      : "text-foreground/80 hover:bg-secondary/80",
                  )}
                >
                  {section.title}
                </button>
              ))}
            </nav>
          </div>
        </aside>

        <div ref={containerRef} className="space-y-6 min-w-0">
          {reader.cover_page && (
            <div className="rounded-lg border border-border bg-secondary/10">
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
                Show Cover Page
              </button>
              {showCoverPage && (
                <div className="border-t border-border px-4 py-4">
                  <CoverPageContent coverPage={reader.cover_page} />
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

function CoverPageContent({ coverPage }: { coverPage: FilingCoverPage }) {
  return (
    <div
      className="filing-cover-content space-y-3 text-sm leading-6 text-muted-foreground"
      dangerouslySetInnerHTML={{ __html: coverPage.content_html }}
    />
  );
}
