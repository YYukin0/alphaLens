import { motion } from "framer-motion";
import {
  Brain,
  FileSearch,
  LineChart,
  Newspaper,
  ScrollText,
  Sparkles,
} from "lucide-react";
import { SectionShell } from "./SectionShell";
import { easeOut, fadeUp, staggerContainer } from "./motion";

const SOURCES = [
  { icon: ScrollText, label: "SEC Filings", angle: 0 },
  { icon: LineChart, label: "Financials", angle: 60 },
  { icon: Brain, label: "AI Reasoning", angle: 120 },
  { icon: Newspaper, label: "News", angle: 180 },
  { icon: FileSearch, label: "Market Data", angle: 240 },
  { icon: Sparkles, label: "Events", angle: 300 },
];

export function WhatIsSection() {
  return (
    <SectionShell id="what-is" label="// What is DeepEquity">
      <div className="grid items-center gap-16 lg:grid-cols-2">
        <div>
          <h2 className="font-display text-4xl leading-tight text-white md:text-5xl">
            One research workflow.
            <br />
            Every source that matters.
          </h2>
          <p className="mt-6 text-lg leading-8 text-white/60">
            DeepEquity combines SEC filings, financial statements, earnings transcripts, market data,
            corporate events, and AI reasoning into a single institutional research environment — so
            analysts spend less time gathering data and more time forming conviction.
          </p>
        </div>

        <div className="relative mx-auto flex h-80 w-80 items-center justify-center">
          <div className="absolute inset-0 rounded-full border border-white/8" />
          <div className="absolute inset-8 rounded-full border border-brand/20" />
          <div className="absolute inset-16 rounded-full bg-brand/10 blur-2xl" />
          <div className="relative z-10 flex h-24 w-24 items-center justify-center rounded-full border border-brand/30 bg-[#0b1017]">
            <span className="text-center text-xs font-semibold uppercase tracking-wider text-brand">
              Deep
              <br />
              Equity
            </span>
          </div>
          {SOURCES.map(({ icon: Icon, label, angle }) => {
            const rad = (angle * Math.PI) / 180;
            const x = Math.cos(rad) * 128;
            const y = Math.sin(rad) * 128;
            return (
              <motion.div
                key={label}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: angle / 400 }}
                className="absolute flex flex-col items-center gap-2"
                style={{ transform: `translate(${x}px, ${y}px)` }}
              >
                <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-brand">
                  <Icon className="h-5 w-5" />
                </div>
                <span className="text-xs text-white/55">{label}</span>
              </motion.div>
            );
          })}
        </div>
      </div>
    </SectionShell>
  );
}

const FEATURES = [
  {
    icon: FileSearch,
    title: "SEC Filing Search",
    description: "Search, read, and analyze 10-K, 10-Q, 8-K and more with structured navigation.",
  },
  {
    icon: Brain,
    title: "AI Research",
    description: "Ask anything about a company. Get answers grounded in original filings.",
  },
  {
    icon: LineChart,
    title: "Financial Statements",
    description: "Income statement, balance sheet, cash flow, and key metrics in one view.",
  },
  {
    icon: Sparkles,
    title: "Event Intelligence",
    description: "Track earnings, guidance, insider activity, M&A, buybacks, and risk changes.",
  },
  {
    icon: ScrollText,
    title: "Filing Reader",
    description: "Premium reading experience with TOC, search, and section-level analysis.",
  },
  {
    icon: Newspaper,
    title: "Market Data",
    description: "Historical prices, valuation metrics, and performance context alongside filings.",
  },
];

export function FeaturesSection() {
  return (
    <SectionShell id="features" label="// Everything in one platform" className="border-t border-white/[0.06]">
      <h2 className="max-w-3xl font-display text-4xl leading-tight text-white md:text-5xl">
        Everything you need.
        <br />
        All in one place.
      </h2>

      <motion.div
        variants={staggerContainer}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-80px" }}
        className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      >
        {FEATURES.map((feature) => (
          <motion.div
            key={feature.title}
            variants={fadeUp}
            transition={{ duration: 0.6, ease: easeOut }}
            className="group rounded-2xl border border-white/8 bg-white/[0.02] p-6 transition-colors hover:border-brand/30 hover:bg-white/[0.04]"
          >
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-brand/10 text-brand transition-transform group-hover:scale-105">
              <feature.icon className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
            <p className="mt-2 text-sm leading-6 text-white/55">{feature.description}</p>
          </motion.div>
        ))}
      </motion.div>
    </SectionShell>
  );
}
