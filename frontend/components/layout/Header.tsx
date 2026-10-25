"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth-context";

export function Header() {
  const { user, logout } = useAuth();

  // No navigation here on purpose: the only page that needs signed-out
  // visitors kept out is /history, and it already redirects itself away
  // (via its own effect watching `user`) the instant this clears the auth
  // state - having the Header *also* navigate raced against that guard
  // and the two could land on different URLs depending on which ran last.
  // Every other page is intentionally accessible without an account, so
  // logging out from one of them should just flip the header, not force
  // a redirect.

  return (
    <header className="border-b border-border">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-sm font-bold text-accent-foreground">
            IV
          </span>
          <span className="text-sm font-semibold tracking-tight">InterVue AI</span>
        </Link>
        <div className="flex items-center gap-4">
          <span className="hidden text-xs text-muted sm:inline">
            ML Engineer Internship Interview Practice
          </span>
          {user ? (
            <div className="flex items-center gap-3 text-sm">
              <Link
                href="/history"
                className="text-muted underline-offset-2 hover:text-foreground hover:underline"
              >
                My Interviews
              </Link>
              <button
                type="button"
                onClick={logout}
                className="text-muted underline-offset-2 hover:text-foreground hover:underline"
              >
                Log out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3 text-sm">
              <Link
                href="/login"
                className="text-muted underline-offset-2 hover:text-foreground hover:underline"
              >
                Log in
              </Link>
              <Link
                href="/register"
                className="rounded-full bg-accent px-3 py-1.5 text-xs font-medium text-accent-foreground transition hover:bg-accent-hover"
              >
                Sign up
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
