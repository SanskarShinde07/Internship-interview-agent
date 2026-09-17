"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { BackButton } from "@/components/ui/BackButton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

export default function LoginPage() {
  const router = useRouter();
  const { user, isLoading: isAuthLoading, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Landing here already signed in (e.g. the back button after a
    // previous login) should bounce away, not show the form again.
    if (!isAuthLoading && user) {
      router.replace("/history");
    }
  }, [user, isAuthLoading, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
      // replace, not push: once logged in, the back button shouldn't
      // return to the login form.
      router.replace("/history");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not log in. Please try again.",
      );
      setIsSubmitting(false);
    }
  }

  return (
    <main className="relative flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="absolute top-6 left-6">
        <BackButton />
      </div>
      <Card className="w-full max-w-md">
        <h1 className="mb-2 text-2xl font-semibold">Log in</h1>
        <p className="mb-6 text-sm text-muted">
          Sign in to keep track of your past interviews and reports.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Email
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Password
            <Input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </label>
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" disabled={isSubmitting} className="mt-2">
            {isSubmitting ? "Logging in..." : "Log in"}
          </Button>
        </form>
        <div className="mt-4 flex flex-col items-center gap-2 text-center text-sm">
          <Link
            href="/forgot-password"
            className="text-muted underline-offset-2 hover:text-foreground hover:underline"
          >
            Forgot your password?
          </Link>
          <p className="text-muted">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-accent hover:underline">
              Sign up
            </Link>
          </p>
        </div>
      </Card>
    </main>
  );
}
