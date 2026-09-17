import Link from "next/link";

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
  return (
    <main className="flex flex-1 flex-col items-center px-6">
      <section className="flex flex-col items-center gap-6 py-20 text-center sm:py-28">
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
          href="/setup"
          className="rounded-full bg-accent px-7 py-3 font-medium text-accent-foreground transition hover:bg-accent-hover"
        >
          Start Mock Interview
        </Link>
      </section>

      <section className="grid w-full max-w-4xl gap-4 pb-24 sm:grid-cols-3">
        {FEATURES.map((feature) => (
          <div key={feature.title} className="rounded-2xl border border-border bg-surface p-6">
            <h2 className="mb-2 text-sm font-semibold">{feature.title}</h2>
            <p className="text-sm text-muted">{feature.description}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
