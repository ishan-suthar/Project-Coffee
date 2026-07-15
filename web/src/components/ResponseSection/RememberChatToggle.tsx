"use client";

import { useState } from "react";
import { useChatStore } from "@/store/chatStore";
import type { ChatMessage } from "@/lib/chat";

interface RememberChatToggleProps {
  sessionId: string;
  rememberChat: boolean;
  lastAssistantMessage: ChatMessage | null;
  hasAnyPriorAttachment: boolean;
}

/**
 * Brew 46 (docs/design/conversation-memory-design.md Section 1): a
 * per-session, user-controlled toggle for whether prior turns are sent
 * back to the model. Optimistic - chatStore.setRememberChat() flips the
 * local sessions array immediately and reverts it if the PATCH fails.
 */
export function RememberChatToggle({
  sessionId,
  rememberChat,
  lastAssistantMessage,
  hasAnyPriorAttachment,
}: RememberChatToggleProps) {
  const setRememberChat = useChatStore((s) => s.setRememberChat);
  const [pending, setPending] = useState(false);

  async function handleToggle() {
    setPending(true);
    try {
      await setRememberChat(sessionId, !rememberChat);
    } catch {
      // chatStore.setRememberChat already reverted the optimistic flip -
      // nothing further to do here.
    } finally {
      setPending(false);
    }
  }

  const historyTurns = lastAssistantMessage?.historyTurnsIncluded ?? null;
  const historyTokens = lastAssistantMessage?.historyTokensEst ?? null;
  const showHint = rememberChat && historyTurns !== null;

  return (
    <div
      className="flex flex-wrap items-center gap-2 border-b border-caramel px-6 py-2 text-xs"
      data-testid="remember-chat-row"
    >
      <label className="flex items-center gap-2 text-espresso">
        <button
          type="button"
          role="switch"
          aria-checked={rememberChat}
          aria-label="Remember chat"
          data-testid="remember-chat-toggle"
          onClick={handleToggle}
          disabled={pending}
          title="Turning this off never deletes anything - it only stops sending prior turns to the model. Turning it back on resumes with everything already stored in this session."
          className={`relative h-5 w-9 rounded-full transition-colors ${
            rememberChat ? "bg-crema-amber" : "bg-caramel"
          } disabled:opacity-50`}
        >
          <span
            aria-hidden="true"
            className={`absolute top-0.5 h-4 w-4 rounded-full bg-cream transition-transform ${
              rememberChat ? "translate-x-4" : "translate-x-0.5"
            }`}
          />
        </button>
        Remember chat
      </label>

      {showHint && (
        <span data-testid="remember-chat-hint" className="text-medium-roast">
          {historyTurns} {historyTurns === 1 ? "turn" : "turns"}, ~{formatTokenCount(historyTokens ?? 0)} tokens
          carried
        </span>
      )}

      {!rememberChat && hasAnyPriorAttachment && (
        <span data-testid="remember-chat-attachment-hint" className="text-medium-roast">
          Turn on Remember chat to ask follow-ups about your attachments.
        </span>
      )}
    </div>
  );
}

function formatTokenCount(tokens: number): string {
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`;
  return String(tokens);
}
