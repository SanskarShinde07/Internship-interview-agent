import Link from "next/link";

export function Header() {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-sm font-bold text-accent-foreground">
            IV
          </span>
          <span className="text-sm font-semibold tracking-tight">InterVue AI</span>
        </Link>
        <span className="hidden text-xs text-muted sm:inline">
          ML Engineer Internship Interview Practice
        </span>
      </div>
    </header>
  );
}
