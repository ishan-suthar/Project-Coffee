"use client";

import { useEffect, useState } from "react";
import type { ChatMessage } from "@/lib/chat";
import { useChatStore } from "@/store/chatStore";
import { escalationReasonText } from "@/components/ResponseSection/escalationReasonText";

interface EscalationApprovalCardProps {
  message: ChatMessage;
}

/** Requirement 1: what failed (plain language), the premium Bean alias,
 * estimated cost, and two buttons - rendered while a message's
 * escalation is genuinely awaiting a decision (live pause, or a card
 * reconstructed via recoverPendingEscalation after a reload - see
 * docs/design/escalation-approval-ui-design.md Section 4.1). Disappears
 * on its own once the message's latestEvent moves past
 * escalation_pending (live path) or isStreaming flips false (recovered
 * path, once polling finds the result) - no local "resolved" flag
 * needed here. */
export function EscalationApprovalCard({ message }: EscalationApprovalCardProps) {
  const approveEscalation = useChatStore((s) => s.approveEscalation);
  const [decision, setDecision] = useState<"approve" | "decline" | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const escalation = message.escalation;

  useEffect(() => {
    if (!escalation?.decisionDeadline) return;
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, [escalation?.decisionDeadline]);

  if (escalation === null || message.requestId === null) return null;

  const secondsLeft = escalation.decisionDeadline
    ? Math.max(0, Math.round((new Date(escalation.decisionDeadline).getTime() - now) / 1000))
    : null;

  async function handleDecision(approve: boolean) {
    if (decision !== null) return; // already sent - ignore a rapid second click client-side too
    setDecision(approve ? "approve" : "decline");
    await approveEscalation(message.requestId as string, approve);
  }

  return (
    <div
      className="mt-2 rounded border border-crema-amber bg-cream p-3 text-sm text-espresso"
      data-testid="escalation-approval-card"
    >
      <p data-testid="escalation-approval-reason">{escalationReasonText(escalation.reason)}</p>
      <p className="mt-1 text-medium-roast">
        Brew it again with{" "}
        <span className="font-mono" data-testid="escalation-approval-premium-alias">
          {escalation.premiumBeanAlias ?? "no premium Bean"}
        </span>{" "}
        for an estimated{" "}
        <span className="font-mono tabular-nums" data-testid="escalation-approval-cost">
          ${escalation.estCostUsd.toFixed(4)}
        </span>
        ?
      </p>

      {secondsLeft !== null && (
        <p className="mt-1 text-xs text-medium-roast" data-testid="escalation-approval-countdown">
          {decision !== null
            ? "Waiting for the premium response..."
            : secondsLeft > 0
              ? `Auto-declining in ${secondsLeft}s if no decision is made.`
              : "This decision has timed out - keeping the draft."}
        </p>
      )}

      <div className="mt-2 flex gap-2">
        <button
          type="button"
          data-testid="escalation-approve-button"
          onClick={() => handleDecision(true)}
          disabled={decision !== null}
          className="rounded bg-crema-amber px-3 py-1.5 text-cream transition hover:opacity-90 disabled:opacity-50"
        >
          Brew premium
        </button>
        <button
          type="button"
          data-testid="escalation-decline-button"
          onClick={() => handleDecision(false)}
          disabled={decision !== null}
          className="rounded border border-caramel px-3 py-1.5 text-espresso transition hover:bg-latte disabled:opacity-50"
        >
          Keep the cheap cup
        </button>
      </div>
    </div>
  );
}
