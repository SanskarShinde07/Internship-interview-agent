export default function LandingPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">InterVue AI</h1>
      <p className="max-w-xl text-balance text-lg text-neutral-500">
        Adaptive AI voice interviewer for Machine Learning Engineer internships. Practice a real
        interview loop — Python, ML, NLP, projects, scenarios, and behavioral rounds — with
        difficulty that adapts to you.
      </p>
      <button
        type="button"
        className="rounded-full bg-neutral-900 px-6 py-3 font-medium text-white transition hover:bg-neutral-700 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
      >
        Start Mock Interview
      </button>
    </main>
  );
}
