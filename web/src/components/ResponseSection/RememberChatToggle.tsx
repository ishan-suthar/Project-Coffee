"use client";

import { useState } from "react";
import { useChatStore } from "@/store/chatStore";
import type { ChatMessage } from "@/lib/chat";
import type { HistoryDropReason } from "@/lib/events";

/**
 * Brew 57: how much dropped material is enough to be worth suggesting the
 * Pantry for. Roughly a page of text - below this, a trim is ordinary
 * conversation ageing out and nagging about it would be noise.
 *
 * Deliberately a frontend constant rather than an event field or a
 * settings.yaml value: when to show a hint is a presentation choice, and
 * the event contract carries facts, not decisions about when to nag.
 */
export const PANTRY_HINT_MIN_DROPPED_CHARS = 2000;

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

  // Brew 57: a drop notice appears if and only if something was actually
  // dropped. A real 0 (toggle on, nothing dropped) and null (toggle off)
  // both render nothing - silence is the correct signal for "nothing was
  // dropped", and the "N turns carried" hint above already affirms what
  // *was* sent.
  const turnsDropped = lastAssistantMessage?.historyTurnsDropped ?? null;
  const charsDropped = lastAssistantMessage?.historyCharsDropped ?? null;
  const dropReason = lastAssistantMessage?.historyDropReason ?? null;
  const showDropNotice = rememberChat && turnsDropped !== null && turnsDropped > 0;
  const showPantryHint =
    showDropNotice &&
    (dropReason === "single_turn_too_large" ||
      (charsDropped ?? 0) >= PANTRY_HINT_MIN_DROPPED_CHARS);

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
            className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-cream transition-transform ${
              rememberChat ? "translate-x-4" : "translate-x-0"
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

      {showDropNotice && (
        <span data-testid="remember-chat-drop-notice" className="text-medium-roast">
          {describeDrop(dropReason, turnsDropped as number)}
          {showPantryHint && (
            <> Long documents belong in the Pantry - add it to knowledge/ and use Use Pantry.</>
          )}
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

/**
 * Brew 57: one sentence per drop reason. Each names a different remedy,
 * which is why the reasons are not collapsed into one message - see
 * router/app/history.py's HistoryDropReason. Informational tone, no
 * warning colour or icon: trimming is normal behaviour the user simply
 * needs to be able to see, not an error.
 */
function describeDrop(reason: HistoryDropReason | null, turnsDropped: number): string {
  const turnWord = turnsDropped === 1 ? "turn" : "turns";

  switch (reason) {
    case "current_prompt_fills_window":
      return "This message alone fills the history window, so no earlier turns were sent.";
    case "single_turn_too_large":
      return `${turnsDropped} earlier ${turnWord} dropped - one was too large for the window on its own.`;
    case "window_full":
      return `${turnsDropped} earlier ${turnWord} dropped to fit the window.`;
    default:
      // The router sends a reason whenever turnsDropped > 0, so this is
      // unreachable today. Kept honest rather than asserting: an
      // unrecognised reason from a newer router still reports the fact.
      return `${turnsDropped} earlier ${turnWord} dropped to fit the window.`;
  }
}

function formatTokenCount(tokens: number): string {
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`;
  return String(tokens);
}
