"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

import { ApiError, getCoachMessages, postCoachMessage } from "@/lib/api-client";
import type { CoachMessageItem } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { MessageBubble } from "@/components/coach/MessageBubble";

const SUGGESTED_PROMPTS = [
  "What should I study next?",
  "Why did I score low overall?",
  "What does a strong scenario-round answer look like?",
];

export default function CoachPage() {
  const params = useParams<{ sessionId: string }>();
  const [messages, setMessages] = useState<CoachMessageItem[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    getCoachMessages(params.sessionId)
      .then((res) => {
        if (!cancelled) setMessages(res.messages);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Could not load your coach chat.");
      })
      .finally(() => {
        if (!cancelled) setIsLoadingHistory(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!text.trim() || isSending) return;
    setIsSending(true);
    setError(null);
    setMessages((prev) => [
      ...prev,
      { role: "USER", content: text, referenced_question_id: null },
    ]);
    setInput("");
    try {
      const result = await postCoachMessage(params.sessionId, text);
      setMessages((prev) => [
        ...prev,
        { role: "ASSISTANT", content: result.reply, referenced_question_id: null },
      ]);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "The coach couldn't respond. Please try again.",
      );
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold">Post-Interview Coach</h1>
        <p className="text-sm text-neutral-500">
          Ask about your performance, specific answers, or what to study next.
        </p>
      </div>

      <Card className="flex max-h-[60vh] min-h-[400px] flex-1 flex-col gap-3 overflow-y-auto">
        {isLoadingHistory ? (
          <p className="text-sm text-neutral-500">Loading conversation...</p>
        ) : messages.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
            <p className="text-sm text-neutral-500">Ask me anything about your interview.</p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => sendMessage(prompt)}
                  className="rounded-full border border-neutral-300 px-3 py-1.5 text-xs hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </Card>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage(input);
        }}
        className="flex gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the coach..."
          className="flex-1 rounded-full border border-neutral-300 px-4 py-2 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
          disabled={isSending}
        />
        <Button type="submit" disabled={isSending || !input.trim()}>
          Send
        </Button>
      </form>
    </main>
  );
}
