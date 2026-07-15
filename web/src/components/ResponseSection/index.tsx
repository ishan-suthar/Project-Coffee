"use client";

import { useChatStore } from "@/store/chatStore";
import type { ChatMessage } from "@/lib/chat";
import { MessageBubble } from "@/components/ResponseSection/MessageBubble";
import { RememberChatToggle } from "@/components/ResponseSection/RememberChatToggle";

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
  // Brew 46: the toggle reads remember_chat off the sessions list (the
  // same GET /v1/sessions data the Sidebar already fetches), not a
  // second endpoint.
  const rememberChat = useChatStore((s) =>
    s.sessions.find((session) => session.id === s.activeSessionId)?.remember_chat
  );

  if (activeSessionId === null && messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-medium-roast">
        <p>Place an order below to get started.</p>
      </div>
    );
  }

  const lastAssistantMessage = [...messages].reverse().find((m) => m.role === "assistant") ?? null;
  const hasAnyPriorAttachment = messages.some((m) => m.hasAttachments);

  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden" data-testid="response-section">
      {activeSessionId !== null && rememberChat !== undefined && (
        <RememberChatToggle
          sessionId={activeSessionId}
          rememberChat={rememberChat}
          lastAssistantMessage={lastAssistantMessage}
          hasAnyPriorAttachment={hasAnyPriorAttachment}
        />
      )}
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </div>
    </div>
  );
}
