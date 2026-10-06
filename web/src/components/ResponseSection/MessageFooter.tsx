"use client";

import { useEffect, useState } from "react";
import type { ChatMessage } from "@/lib/chat";
import { useChatStore } from "@/store/chatStore";
import * as api from "@/lib/api";
import type { Bean, Rating } from "@/lib/events";

interface MessageFooterProps {
  message: ChatMessage;
}

const RATING_LABELS: Record<Rating, string> = {
  good: "Good",
  needed_fixing: "Needed fixing",
  failed: "Failed",
};

export function MessageFooter({ message }: MessageFooterProps) {
  const rate = useChatStore((s) => s.rate);
  const rebrew = useChatStore((s) => s.rebrew);
  const [beans, setBeans] = useState<Bean[]>([]);
  const [overrideAlias, setOverrideAlias] = useState<string>("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.listBeans().then(setBeans).catch(() => setBeans([]));
  }, []);

  async function handleCopy() {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  async function handleRebrew() {
    await rebrew(message, overrideAlias || undefined);
  }

  if (message.requestId === null) return null; // user messages have no footer

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs" data-testid="message-footer">
      {(Object.keys(RATING_LABELS) as Rating[]).map((rating) => (
        <button
          key={rating}
          type="button"
          data-testid={`rate-${rating}`}
          onClick={() => rate(message.requestId as string, rating)}
          className={`rounded border px-2 py-1 transition hover:bg-latte ${
            message.rating === rating ? "border-crema-amber text-crema-amber" : "border-caramel text-espresso"
          }`}
        >
          {RATING_LABELS[rating]}
        </button>
      ))}

      <button
        type="button"
        onClick={handleCopy}
        className="rounded border border-caramel px-2 py-1 text-espresso transition hover:bg-latte"
      >
        {copied ? "Copied" : "Copy"}
      </button>

      <select
        aria-label="Bean override for re-brew"
        value={overrideAlias}
        onChange={(e) => setOverrideAlias(e.target.value)}
        className="rounded border border-caramel bg-cream px-1 py-1 font-mono text-espresso"
      >
        <option value="">Same Bean</option>
        {beans
          .filter((bean) => bean.available)
          .map((bean) => (
            <option key={bean.alias} value={bean.alias}>
              {bean.alias}
            </option>
          ))}
      </select>

      <button
        type="button"
        data-testid="rebrew-button"
        onClick={handleRebrew}
        className="rounded border border-caramel px-2 py-1 text-espresso transition hover:bg-latte"
      >
        Re-brew
      </button>
    </div>
  );
}
