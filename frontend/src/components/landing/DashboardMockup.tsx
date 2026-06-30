import { motion } from "framer-motion";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { Badge } from "@/components/ui/badge";
import { easeOut, scaleIn, staggerContainer } from "./motion";

const CHART = [
  { d: "Jan", v: 182 },
  { d: "Feb", v: 186 },
  { d: "Mar", v: 179 },
  { d: "Apr", v: 191 },
  { d: "May", v: 188 },
  { d: "Jun", v: 196 },
];

const EVENTS = [
  { title: "Q2 earnings beat consensus", tag: "Positive", tone: "text-brand" },
  { title: "New 10-Q filed — MD&A updated", tag: "Neutral", tone: "text-white/60" },
  { title: "Risk factors expanded on AI regulation", tag: "Review", tone: "text-amber-300" },
];

export function DashboardMockup() {
  return (
    <motion.div
      variants={scaleIn}
      transition={{ duration: 0.9, ease: easeOut, delay: 0.15 }}
      className="relative"
    >
      <div className="absolute -inset-8 rounded-[2rem] bg-brand/10 blur-3xl" />
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#0b1017]/90 shadow-2xl shadow-black/40 ring-1 ring-white/5">
        <div className="flex items-center justify-between border-b border-white/8 px-5 py-3">
          <div>
            <p className="text-xs uppercase tracking-wider text-white/45">Company Dashboard</p>
            <p className="text-lg font-semibold text-white">Apple Inc. · AAPL</p>
          </div>
          <Badge className="bg-brand/15 text-brand hover:bg-brand/15">Live</Badge>
        </div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="grid gap-4 p-5 md:grid-cols-5"
        >
          <motion.div variants={scaleIn} className="md:col-span-3 rounded-xl border border-white/8 bg-white/[0.03] p-4">
            <div className="mb-3 flex items-end justify-between">
              <div>
                <p className="text-3xl font-display text-white">$195.83</p>
                <p className="text-sm text-brand">+1.28% today</p>
              </div>
              <p className="text-xs text-white/45">1Y performance</p>
            </div>
            <div className="h-36">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={CHART}>
                  <defs>
                    <linearGradient id="brandFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3ECF8E" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#3ECF8E" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="v"
                    stroke="#3ECF8E"
                    strokeWidth={2}
                    fill="url(#brandFill)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          <motion.div variants={scaleIn} className="md:col-span-2 space-y-3">
            <div className="rounded-xl border border-white/8 bg-white/[0.03] p-4">
              <p className="text-xs uppercase tracking-wider text-white/45">AI Summary</p>
              <p className="mt-2 text-sm leading-6 text-white/75">
                Revenue growth accelerated in Services. Gross margin expanded 120bps QoQ. Management
                raised full-year outlook citing installed base strength.
              </p>
            </div>
            <div className="rounded-xl border border-white/8 bg-white/[0.03] p-4">
              <p className="text-xs uppercase tracking-wider text-white/45">Key Metrics</p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <Metric label="Market Cap" value="$3.0T" />
                <Metric label="P/E" value="29.4x" />
                <Metric label="Rev Growth" value="+6.1%" />
                <Metric label="FCF Yield" value="3.8%" />
              </div>
            </div>
          </motion.div>

          <motion.div variants={scaleIn} className="md:col-span-5 rounded-xl border border-white/8 bg-white/[0.03] p-4">
            <p className="mb-3 text-xs uppercase tracking-wider text-white/45">Recent Events</p>
            <div className="space-y-2">
              {EVENTS.map((event) => (
                <div
                  key={event.title}
                  className="flex items-center justify-between rounded-lg border border-white/6 bg-black/20 px-3 py-2"
                >
                  <p className="text-sm text-white/80">{event.title}</p>
                  <span className={`text-xs font-medium ${event.tone}`}>{event.tag}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </div>
    </motion.div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-white/45">{label}</p>
      <p className="font-medium text-white">{value}</p>
    </div>
  );
}
