import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Bot, FileText, LayoutDashboard } from "lucide-react";
import { AnimatedCounter } from "./AnimatedCounter";
import { SectionShell } from "./SectionShell";
import { easeOut, fadeUp, staggerContainer } from "./motion";

export function PlatformPreviewSection() {
  return (
    <SectionShell id="preview" label="// Platform preview" className="border-t border-white/[0.06]">
      <h2 className="max-w-3xl font-display text-4xl leading-tight text-white md:text-5xl">
        Powerful tools.
        <br />
        Beautiful experience.
      </h2>
      <p className="mt-4 max-w-2xl text-lg text-white/55">
        Designed for long-form research sessions — not generic dashboards pasted together.
      </p>

      <motion.div
        variants={staggerContainer}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-60px" }}
        className="mt-12 space-y-6"
      >
        <PreviewPanel
          icon={Bot}
          title="AI Research Assistant"
          description="Ask natural-language questions and receive cited answers from SEC source documents."
          content={
            <div className="space-y-3 p-5">
              <ChatBubble role="user" text="What changed in Apple's latest 10-Q MD&A?" />
              <ChatBubble
                role="ai"
                text="Services revenue grew 14% YoY. Gross margin expanded 120bps. Management noted stronger-than-expected iPhone demand in emerging markets. [Item 7, Q2 10-Q]"
              />
            </div>
          }
        />
        <PreviewPanel
          icon={FileText}
          title="Structured Filing Reader"
          description="Navigate Items, search within filings, and highlight risk, MD&A, and financial sections."
          content={
            <div className="grid gap-4 p-5 md:grid-cols-[180px_1fr]">
              <div className="space-y-1 rounded-xl border border-white/8 bg-black/20 p-3 text-xs text-white/55">
                <p className="font-medium text-white/80">Table of Contents</p>
                <p className="text-brand">● Item 1A · Risk Factors</p>
                <p>● Item 7 · MD&A</p>
                <p>● Item 8 · Financials</p>
              </div>
              <div className="rounded-xl border border-white/8 bg-black/20 p-4 font-serif text-sm leading-7 text-white/70">
                Item 7. Management&apos;s Discussion and Analysis of Financial Condition and Results of
                Operations. Revenue increased primarily due to growth in Services and iPhone...
              </div>
            </div>
          }
        />
        <PreviewPanel
          icon={LayoutDashboard}
          title="Company Research Workspace"
          description="Profile, filings, financials, metrics, and AI notes in a unified company view."
          content={
            <div className="grid gap-3 p-5 sm:grid-cols-3">
              <MiniStat label="Filings" value="131" />
              <MiniStat label="Events" value="24" />
              <MiniStat label="Latest" value="10-Q" />
            </div>
          }
        />
      </motion.div>
    </SectionShell>
  );
}

function PreviewPanel({
  icon: Icon,
  title,
  description,
  content,
}: {
  icon: typeof Bot;
  title: string;
  description: string;
  content: React.ReactNode;
}) {
  return (
    <motion.div
      variants={fadeUp}
      transition={{ duration: 0.7, ease: easeOut }}
      className="overflow-hidden rounded-2xl border border-white/10 bg-[#0b1017]/80"
    >
      <div className="border-b border-white/8 px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand">
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">{title}</h3>
            <p className="text-sm text-white/50">{description}</p>
          </div>
        </div>
      </div>
      {content}
    </motion.div>
  );
}

function ChatBubble({ role, text }: { role: "user" | "ai"; text: string }) {
  return (
    <div
      className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-6 ${
        role === "user"
          ? "ml-auto bg-white/8 text-white/80"
          : "border border-brand/20 bg-brand/5 text-white/75"
      }`}
    >
      {text}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/8 bg-black/20 p-4">
      <p className="text-xs uppercase tracking-wider text-white/45">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}

const STEPS = [
  { step: "01", title: "Search", description: "Find any company, filing, metric, or research question." },
  { step: "02", title: "Analyze", description: "DeepEquity reads filings, financials, and events with AI assistance." },
  { step: "03", title: "Generate insights", description: "Produce cited summaries, comparisons, and investment-ready notes." },
];

export function HowItWorksSection() {
  return (
    <SectionShell id="how-it-works" label="// How it works" className="border-t border-white/[0.06]">
      <h2 className="font-display text-4xl leading-tight text-white md:text-5xl">
        Research smarter.
        <br />
        In three simple steps.
      </h2>

      <div className="relative mt-14 grid gap-6 md:grid-cols-3">
        <div className="pointer-events-none absolute left-[16%] right-[16%] top-10 hidden h-px bg-gradient-to-r from-transparent via-brand/40 to-transparent md:block" />
        {STEPS.map((item, index) => (
          <motion.div
            key={item.step}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: index * 0.12, ease: easeOut }}
            className="relative rounded-2xl border border-white/8 bg-white/[0.02] p-6"
          >
            <p className="font-mono text-sm text-brand">{item.step}</p>
            <h3 className="mt-3 text-xl font-semibold text-white">{item.title}</h3>
            <p className="mt-2 text-sm leading-6 text-white/55">{item.description}</p>
          </motion.div>
        ))}
      </div>
    </SectionShell>
  );
}

const AUDIENCES = [
  { title: "Investment Funds", description: "Accelerate idea generation and due diligence with cited AI research." },
  { title: "Equity Research", description: "Cover more names without sacrificing depth on filings and financials." },
  { title: "Family Offices", description: "Monitor portfolio companies, events, and risk changes in one place." },
  { title: "Institutional Investors", description: "Standardize research workflows across analysts and strategies." },
  { title: "Corporate Strategy", description: "Benchmark peers, track disclosures, and analyze competitive shifts." },
];

export function AudienceSection() {
  return (
    <SectionShell id="audience" className="border-t border-white/[0.06]">
      <h2 className="font-display text-4xl leading-tight text-white md:text-5xl">
        Built for professionals
        <br />
        who take research seriously.
      </h2>
      <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {AUDIENCES.map((item, index) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: index * 0.06 }}
            className="rounded-2xl border border-white/8 bg-white/[0.02] p-5"
          >
            <h3 className="font-semibold text-white">{item.title}</h3>
            <p className="mt-2 text-sm leading-6 text-white/55">{item.description}</p>
          </motion.div>
        ))}
      </div>
    </SectionShell>
  );
}

export function WhyAISection() {
  return (
    <SectionShell id="why-ai" label="// Why AI matters" className="border-t border-white/[0.06]">
      <div className="grid gap-10 lg:grid-cols-2">
        <div>
          <h2 className="font-display text-4xl leading-tight text-white md:text-5xl">
            Not another data terminal.
            <br />
            A research workflow.
          </h2>
          <p className="mt-6 text-lg leading-8 text-white/60">
            Traditional platforms excel at data access. DeepEquity excels at research velocity — connecting
            source documents, structured analysis, and AI reasoning into one continuous workflow with
            citations you can trust.
          </p>
        </div>
        <div className="space-y-4">
          {[
            "Read filings with structure, not raw HTML chaos.",
            "Extract risks, KPIs, and MD&A with AI — grounded in source text.",
            "Compare quarters and filings without manual copy-paste.",
            "Move from question to cited insight in minutes, not hours.",
          ].map((point) => (
            <div
              key={point}
              className="rounded-xl border border-white/8 bg-white/[0.02] px-4 py-3 text-sm leading-6 text-white/70"
            >
              {point}
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

const METRICS = [
  { value: 12000000, suffix: "+", label: "SEC filing records indexed" },
  { value: 8000, suffix: "+", label: "Public companies covered" },
  { value: 500000, suffix: "+", label: "AI research outputs generated" },
  { value: 24, suffix: "/7", label: "Continuous data refresh" },
];

export function MetricsSection() {
  return (
    <SectionShell id="metrics" className="border-t border-white/[0.06]">
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {METRICS.map((metric, index) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: index * 0.08 }}
            className="rounded-2xl border border-white/8 bg-white/[0.02] p-6"
          >
            <p className="font-display text-4xl text-brand">
              <AnimatedCounter value={metric.value} suffix={metric.suffix} />
            </p>
            <p className="mt-2 text-sm text-white/55">{metric.label}</p>
          </motion.div>
        ))}
      </div>
    </SectionShell>
  );
}

export function FinalCtaSection() {
  return (
    <SectionShell id="cta" className="border-t border-white/[0.06] pb-32">
      <div className="relative overflow-hidden rounded-[2rem] border border-brand/20 bg-gradient-to-br from-brand/10 via-white/[0.02] to-transparent px-8 py-16 text-center md:px-16">
        <div className="pointer-events-none absolute inset-0 landing-grid opacity-20" />
        <h2 className="relative font-display text-4xl leading-tight text-white md:text-5xl">
          Ready to research smarter?
        </h2>
        <p className="relative mx-auto mt-4 max-w-xl text-lg text-white/60">
          Join the next generation of AI-native equity research. Explore the platform or request early access.
        </p>
        <div className="relative mt-8 flex flex-wrap justify-center gap-3">
          <a
            href="mailto:contact@deepequity.local?subject=DeepEquity%20Early%20Access"
            className="rounded-full border border-white/12 bg-white/[0.03] px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-white/[0.06]"
          >
            Get Early Access
          </a>
          <Link
            to="/companies"
            className="inline-flex items-center gap-2 rounded-full bg-brand px-6 py-3 text-sm font-semibold text-[#04120c]"
          >
            Explore Platform
          </Link>
        </div>
      </div>
    </SectionShell>
  );
}

export function LandingFooter() {
  return (
    <footer className="border-t border-white/[0.06] py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-sm text-white/40 md:flex-row">
        <p>© {new Date().getFullYear()} DeepEquity. All rights reserved.</p>
        <div className="flex gap-6">
          <Link to="/companies" className="hover:text-white/70">
            Platform
          </Link>
          <a href="mailto:contact@deepequity.local" className="hover:text-white/70">
            Contact
          </a>
        </div>
      </div>
    </footer>
  );
}
