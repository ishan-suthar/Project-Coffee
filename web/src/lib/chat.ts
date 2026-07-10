import type { Complexity, EscalationReason, Rating, RouterEvent } from "@/lib/events";
import type { AttachmentKind } from "@/lib/attachments";

/** Read-only view of one sent attachment, attached to the user message it
 * was sent with. previewUrl is an in-memory blob URL (image thumbnails
 * only) and is only valid for the current browser session - see
 * docs/design/attachments-design.md Section 11 (no persistence across a
 * page reload). */
export interface AttachmentSummary {
  attachmentId: string;
  filename: string;
  sizeBytes: number;
  kind: AttachmentKind;
  previewUrl: string | null;
}

/** UI-level view of one turn's assistant message, built live from the SSE
 * stream and reconciled with router/EVENT_CONTRACT.md's fields as they
 * arrive. See docs/design/coffee-counter-chat-ui-design.md Section 5.3. */
export interface ChatMessage {
  id: string; // requestId for assistant messages, a local uuid for user messages
  role: "user" | "assistant";
  content: string;
  requestId: string | null; // null for a user message that hasn't been sent yet (never happens today, kept for forward safety)
  isStreaming: boolean;
  latestEvent: RouterEvent | null;
  beanAlias: string | null;
  taskType: string | null;
  complexity: Complexity | null;
  costUsd: number | null;
  latencyMs: number | null;
  escalated: boolean;
  draftQuality: boolean;
  escalation: {
    reason: EscalationReason;
    estCostUsd: number;
    premiumBeanAlias: string | null;
  } | null;
  rating: Rating | null;
  errorMessage: string | null;
  attachments: AttachmentSummary[];
}

export function reduceEventIntoMessage(message: ChatMessage, event: RouterEvent): ChatMessage {
  switch (event.event) {
    case "order_received":
      return { ...message, latestEvent: event };
    case "classifying":
      return { ...message, latestEvent: event };
    case "route_selected":
      return {
        ...message,
        latestEvent: event,
        beanAlias: event.bean_alias,
        taskType: event.task_type,
        complexity: event.complexity,
      };
    case "generating":
      return {
        ...message,
        latestEvent: event,
        content: message.content + (event.text_delta ?? ""),
      };
    case "escalation_pending":
      return {
        ...message,
        latestEvent: event,
        escalation: {
          reason: event.reason,
          estCostUsd: event.est_cost_usd,
          premiumBeanAlias: event.premium_bean_alias,
        },
      };
    case "escalating":
      return { ...message, latestEvent: event, beanAlias: event.bean_alias };
    case "complete":
      return {
        ...message,
        latestEvent: event,
        isStreaming: false,
        beanAlias: event.bean_alias,
        costUsd: event.cost_usd,
        latencyMs: event.latency_ms,
        escalated: event.escalated,
        draftQuality: event.draft_quality,
      };
    case "error":
      return {
        ...message,
        latestEvent: event,
        isStreaming: false,
        errorMessage: event.message,
      };
    case "cancelled":
      return { ...message, latestEvent: event, isStreaming: false };
  }
}

export function newAssistantMessage(requestId: string): ChatMessage {
  return {
    id: requestId,
    role: "assistant",
    content: "",
    requestId,
    isStreaming: true,
    latestEvent: null,
    beanAlias: null,
    taskType: null,
    complexity: null,
    costUsd: null,
    latencyMs: null,
    escalated: false,
    draftQuality: false,
    escalation: null,
    rating: null,
    errorMessage: null,
    attachments: [],
  };
}

export function newUserMessage(
  id: string,
  content: string,
  attachments: AttachmentSummary[] = []
): ChatMessage {
  return {
    id,
    role: "user",
    content,
    requestId: null,
    isStreaming: false,
    latestEvent: null,
    beanAlias: null,
    taskType: null,
    complexity: null,
    costUsd: null,
    latencyMs: null,
    escalated: false,
    draftQuality: false,
    escalation: null,
    rating: null,
    errorMessage: null,
    attachments,
  };
}
