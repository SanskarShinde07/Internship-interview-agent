"use client";

import Link from "next/link";
import { motion } from "framer-motion";

import { useAuth } from "@/lib/auth-context";

const FEATURES = [
  {
    title: "Adaptive difficulty",
    description:
      "Questions get harder or easier in real time based on how you answer — not a fixed script.",
  },
  {
    title: "A real interview loop",
    description:
      "Python, ML theory, NLP, your own projects, scenario reasoning, and behavioral rounds.",
  },
  {
    title: "Recruiter-style report",
    description:
      "Deterministic scores plus AI-written strengths, gaps, and a study roadmap — clearly labeled which is which.",
  },
];

export default function LandingPage() {
  const { user } = useAuth();

  return (
    <main className="flex flex-1 flex-col items-center px-6">
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="flex flex-col items-center gap-6 py-20 text-center sm:py-28"
      >
        <span className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
          ML Engineer Internship Prep
        </span>
        <h1 className="max-w-2xl text-4xl font-bold tracking-tight sm:text-5xl">
          Practice interviews that actually adapt to you
        </h1>
        <p className="max-w-xl text-lg text-balance text-muted">
          InterVue AI runs a full mock interview — Python, ML, NLP, your projects, scenarios, and
          behavioral rounds — with difficulty that adjusts as you go.
        </p>
        <Link
          href={user ? "/setup" : "/login"}
          className="rounded-full bg-accent px-7 py-3 font-medium text-accent-foreground shadow-lg shadow-accent/20 transition hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          Start Mock Interview
        </Link>
        {!user && (
          <p className="text-xs text-muted">
            Sign in required —{" "}
            <Link href="/register" className="text-accent hover:underline">
              create a free account
            </Link>{" "}
            to get started.
          </p>
        )}
      </motion.section>

      <section className="grid w-full max-w-4xl gap-4 pb-24 sm:grid-cols-3">
        {FEATURES.map((feature, index) => (
          <motion.div
            key={feature.title}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut", delay: 0.15 + index * 0.08 }}
            whileHover={{ y: -3 }}
            className="rounded-2xl border border-border bg-surface p-6 shadow-lg shadow-black/20 transition-colors hover:border-accent/40"
          >
            <h2 className="mb-2 text-sm font-semibold">{feature.title}</h2>
            <p className="text-sm text-muted">{feature.description}</p>
          </motion.div>
        ))}
      </section>
    </main>
  );
}
