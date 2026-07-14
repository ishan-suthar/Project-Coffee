import type { EscalationReason } from "@/lib/events";

/**
 * Plain-language failure explanation for the escalation approval card,
 * matching statusText.ts's own data-driven table philosophy - the only
 * thing that needs to change if wording changes.
 */
const REASON_TEXT: Record<EscalationReason, string> = {
  truncated: "The response was cut off before finishing.",
  empty: "The model returned an empty response.",
  refusal_shaped: "The model appears to have declined to answer.",
  caller_reported: "You reported this response as needing a retry.",
};

export function escalationReasonText(reason: EscalationReason): string {
  return REASON_TEXT[reason];
}
