"use client";

import { useState } from "react";
import type { ChatMessage } from "@/lib/chat";

interface MessageHeaderProps {
  message: ChatMessage;
}

/**
 * Bean alias badge, cost pill, latency, and an expandable escalation
 * marker. Never renders a raw model ID - only message.beanAlias, which
 * is always a coffee alias by construction (router/EVENT_CONTRACT.md).
 * See docs/design/coffee-counter-chat-ui-design.md Section 5.3.
 */
export function MessageHeader({ message }: MessageHeaderProps) {
  const [escalationExpanded, setEscalationExpanded] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs" data-testid="message-header">
      {message.beanAlias && (
        <span
          data-testid="bean-alias-badge"
          className="rounded-full border border-caramel bg-latte px-2 py-0.5 font-mono tabular-nums text-espresso"
        >
          {message.beanAlias}
        </span>
      )}

      {message.costUsd !== null && (
        <span
          data-testid="cost-pill"
          className="rounded-full bg-cream px-2 py-0.5 font-mono tabular-nums text-medium-roast"
        >
          ${message.costUsd.toFixed(4)}
        </span>
      )}

      {message.latencyMs !== null && (
        <span className="font-mono tabular-nums text-medium-roast">{message.latencyMs}ms</span>
      )}

      {message.draftQuality && (
        <span
          data-testid="draft-quality-tag"
          className="rounded-full border border-crema-amber px-2 py-0.5 text-crema-amber"
        >
          draft, not escalated
        </span>
      )}

      {message.escalation !== null && (
        <button
          type="button"
          data-testid="escalation-marker"
          onClick={() => setEscalationExpanded((prev) => !prev)}
          className="rounded-full bg-cream px-2 py-0.5 text-medium-roast transition hover:bg-latte"
        >
          escalation: {message.escalation.reason} {escalationExpanded ? "▴" : "▾"}
        </button>
      )}

      {message.escalation !== null && escalationExpanded && (
        <div
          data-testid="escalation-detail"
          className="w-full rounded border border-caramel bg-cream p-2 text-medium-roast"
        >
          <p>Reason: {message.escalation.reason}</p>
          <p>Estimated premium cost: ${message.escalation.estCostUsd.toFixed(4)}</p>
          <p>
            Premium Bean:{" "}
            {message.escalation.premiumBeanAlias ?? "none configured"}
          </p>
        </div>
      )}
    </div>
  );
}
