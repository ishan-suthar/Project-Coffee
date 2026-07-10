"use client";

import { useChatStore } from "@/store/chatStore";
import type { ChatMessage } from "@/lib/chat";
import { MessageBubble } from "@/components/ResponseSection/MessageBubble";

// Stable reference for "no messages yet" - a fresh `[]` literal returned
// from a Zustand selector on every render is a *new* reference each time,
// which Zustand's default Object.is equality sees as "changed" every
// render, causing an infinite render loop (React error #185, "Maximum
// update depth exceeded"). Reusing one constant array fixes it.
const EMPTY_MESSAGES: ChatMessage[] = [];

export function ResponseSection() {
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const messages = useChatStore((s) =>
    s.activeSessionId ? s.messages[s.activeSessionId] ?? EMPTY_MESSAGES : EMPTY_MESSAGES
  );

  if (activeSessionId === null && messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-medium-roast">
        <p>Place an order below to get started.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-4" data-testid="response-section">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}
