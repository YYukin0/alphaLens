import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { cn } from "@/lib/utils";
import { easeOut, fadeUp } from "./motion";

type SectionShellProps = {
  id: string;
  className?: string;
  children: React.ReactNode;
  label?: string;
};

export function SectionShell({ id, className, children, label }: SectionShellProps) {
  const ref = useRef<HTMLElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section id={id} ref={ref} className={cn("scroll-mt-24 py-24 md:py-32", className)}>
      <motion.div
        initial="hidden"
        animate={inView ? "visible" : "hidden"}
        variants={fadeUp}
        transition={{ duration: 0.75, ease: easeOut }}
        className="mx-auto max-w-6xl px-6"
      >
        {label && (
          <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-brand">{label}</p>
        )}
        {children}
      </motion.div>
    </section>
  );
}
