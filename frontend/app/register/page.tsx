"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { BackButton } from "@/components/ui/BackButton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await register(email.trim(), password, displayName.trim() || undefined);
      router.push("/history");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not create your account. Please try again.",
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
        <h1 className="mb-2 text-2xl font-semibold">Create an account</h1>
        <p className="mb-6 text-sm text-muted">
          Optional, but lets you come back and see your past interviews and reports.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Name (optional)
            <Input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Ada Lovelace"
            />
          </label>
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
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
            />
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Confirm password
            <Input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
            />
          </label>
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" disabled={isSubmitting} className="mt-2">
            {isSubmitting ? "Creating account..." : "Sign up"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="text-accent hover:underline">
            Log in
          </Link>
        </p>
      </Card>
    </main>
  );
}
