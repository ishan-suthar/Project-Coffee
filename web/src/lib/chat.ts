import type {
  Complexity,
  EscalationReason,
  HistoryDropReason,
  Rating,
  RouterEvent,
  WebSource,
} from "@/lib/events";
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
    decisionDeadline: string | null;
  } | null;
  rating: Rating | null;
  errorMessage: string | null;
  attachments: AttachmentSummary[];
  // Brew 40: true only for a card reconstructed from GET
  // /v1/sessions/{id}/pending_escalation after a reload - never set by
  // the live SSE path. See docs/design/escalation-approval-ui-design.md
  // Section 3.5 - a recovered card's decision still takes effect
  // server-side, but this client does not resume live token streaming
  // for it.
  pendingEscalationRecovered: boolean;
  // Brew 41: source paths the router actually injected for this request
  // (contract v1.4's pantry_sources). null when Pantry wasn't used or
  // nothing matched - PantrySourceChips renders only when this is a
  // non-empty array, so a message never claims sources it didn't get.
  pantrySources: string[] | null;
  // web search citations Brew: mirrors contract v1.6's web_sources - null
  // when use_web wasn't set or nothing was cited. WebSourceChips renders
  // only when this is a non-empty array, same "never claim a source it
  // didn't get" rule as pantrySources.
  webSources: WebSource[] | null;
  // Brew 46 (docs/design/conversation-memory-design.md Section 1): mirrors
  // contract v1.5's history_turns/history_tokens_est - both null when the
  // session's remember_chat was false, real numbers (including a real 0)
  // otherwise. Promoted onto dedicated fields from latestEvent, same
  // pattern as costUsd/latencyMs below.
  historyTurnsIncluded: number | null;
  historyTokensEst: number | null;
  // Brew 57: mirrors contract v1.7's history_turns_dropped/
  // history_chars_dropped/history_drop_reason - all null when
  // remember_chat was false, historyTurnsDropped a real 0 when the toggle
  // was on and nothing was dropped. RememberChatToggle renders a drop
  // notice if and only if historyTurnsDropped is a positive number.
  historyTurnsDropped: number | null;
  historyCharsDropped: number | null;
  historyDropReason: HistoryDropReason | null;
  // Brew 46: whether this turn had an attachment - true for a live user
  // message with attachments, or a historical message the router reports
  // has_attachments for. Used only to detect "ask the user to turn on
  // Remember chat" - the attachment's own content is never re-fetched
  // for a historical message (attachments stays [] there).
  hasAttachments: boolean;
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
          decisionDeadline: event.decision_deadline,
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
        pantrySources: event.pantry_sources,
        webSources: event.web_sources,
        historyTurnsIncluded: event.history_turns,
        historyTokensEst: event.history_tokens_est,
        historyTurnsDropped: event.history_turns_dropped,
        historyCharsDropped: event.history_chars_dropped,
        historyDropReason: event.history_drop_reason,
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
    case "heartbeat":
      // Keep-alive only (contract v1.3) - never becomes latestEvent, so
      // the scene/status text/approval card never have to know it
      // exists.
      return message;
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
    pendingEscalationRecovered: false,
    pantrySources: null,
    webSources: null,
    historyTurnsIncluded: null,
    historyTokensEst: null,
    historyTurnsDropped: null,
    historyCharsDropped: null,
    historyDropReason: null,
    hasAttachments: false,
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
    pendingEscalationRecovered: false,
    pantrySources: null,
    webSources: null,
    historyTurnsIncluded: null,
    historyTokensEst: null,
    historyTurnsDropped: null,
    historyCharsDropped: null,
    historyDropReason: null,
    hasAttachments: attachments.length > 0,
  };
}
