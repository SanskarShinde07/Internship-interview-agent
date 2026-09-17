"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { ApiError, resetPassword } from "@/lib/api-client";
import { BackButton } from "@/components/ui/BackButton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!token) {
      setError("This reset link is missing its token. Request a new one.");
      return;
    }
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
      await resetPassword(token, password);
      setSuccess(true);
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "This reset link is invalid or has expired. Request a new one.",
      );
      setIsSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-md">
      <h1 className="mb-2 text-2xl font-semibold">Set a new password</h1>
      <p className="mb-6 text-sm text-muted">Choose a new password for your account.</p>

      {success ? (
        <p className="rounded-lg border border-success/30 bg-success-bg p-3 text-sm text-success">
          Your password has been updated. Redirecting you to log in...
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            New password
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
            Confirm new password
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
            {isSubmitting ? "Updating..." : "Update password"}
          </Button>
        </form>
      )}

      <p className="mt-4 text-center text-sm text-muted">
        <Link href="/login" className="text-accent hover:underline">
          Back to log in
        </Link>
      </p>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="relative flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="absolute top-6 left-6">
        <BackButton />
      </div>
      <Suspense fallback={<p className="text-muted">Loading...</p>}>
        <ResetPasswordForm />
      </Suspense>
    </main>
  );
}
