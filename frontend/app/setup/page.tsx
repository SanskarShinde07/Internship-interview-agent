"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError, createSession } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

export default function SetupPage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const session = await createSession({
        display_name: displayName.trim() || undefined,
        email: email.trim() || undefined,
      });
      router.push(`/instructions/${session.session_id}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the interview server. Please try again.",
      );
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <Card className="w-full max-w-md">
        <h1 className="mb-2 text-2xl font-semibold">Before we begin</h1>
        <p className="mb-6 text-sm text-muted">
          Your name is optional and only used to personalize your report. No account or login is
          required.
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
            Email (optional)
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" disabled={isSubmitting} className="mt-2">
            {isSubmitting ? "Starting..." : "Continue"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
