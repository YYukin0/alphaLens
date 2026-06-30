import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Play } from "lucide-react";
import { DashboardMockup } from "./DashboardMockup";
import { easeOut, fadeUp, staggerContainer } from "./motion";

export function HeroSection() {
  return (
    <section id="hero" className="relative overflow-hidden pt-28 pb-20 md:pt-36 md:pb-28">
      <div className="pointer-events-none absolute inset-0 landing-grid opacity-40" />
      <div className="pointer-events-none absolute left-1/2 top-0 h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-brand/10 blur-3xl" />

      <div className="relative mx-auto grid max-w-6xl items-center gap-14 px-6 lg:grid-cols-2">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="max-w-xl"
        >
          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.7, ease: easeOut }}
            className="mb-5 font-mono text-xs uppercase tracking-[0.24em] text-brand"
          >
            AI-native equity research
          </motion.p>
          <motion.h1
            variants={fadeUp}
            transition={{ duration: 0.8, ease: easeOut, delay: 0.05 }}
            className="font-display text-5xl leading-[1.02] tracking-tight text-white md:text-6xl lg:text-7xl"
          >
            Research faster.
            <br />
            <span className="text-brand">Understand deeper.</span>
          </motion.h1>
          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.8, ease: easeOut, delay: 0.12 }}
            className="mt-6 max-w-lg text-lg leading-8 text-white/60"
          >
            DeepEquity is the institutional-grade AI research platform that unifies SEC filings,
            financials, market data, and cited reasoning into one workflow built for serious investors.
          </motion.p>
          <motion.div
            variants={fadeUp}
            transition={{ duration: 0.8, ease: easeOut, delay: 0.18 }}
            className="mt-8 flex flex-wrap gap-3"
          >
            <Link
              to="/companies"
              className="inline-flex items-center gap-2 rounded-full bg-brand px-6 py-3 text-sm font-semibold text-[#04120c] transition-transform hover:scale-[1.02]"
            >
              Explore Platform
              <ArrowRight className="h-4 w-4" />
            </Link>
            <button
              type="button"
              onClick={() => document.getElementById("preview")?.scrollIntoView({ behavior: "smooth" })}
              className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.03] px-6 py-3 text-sm font-medium text-white/85 transition-colors hover:bg-white/[0.06]"
            >
              <Play className="h-4 w-4" />
              Watch Demo
            </button>
          </motion.div>
          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.8, ease: easeOut, delay: 0.24 }}
            className="mt-10 text-xs uppercase tracking-[0.18em] text-white/35"
          >
            Trusted by serious investors
          </motion.p>
        </motion.div>

        <DashboardMockup />
      </div>
    </section>
  );
}
