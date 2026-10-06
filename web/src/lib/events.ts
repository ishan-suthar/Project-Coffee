/**
 * SSE event types mirroring router/EVENT_CONTRACT.md (v1.3) and
 * router/app/events.py exactly. Keep in sync manually - the router has no
 * TypeScript codegen step in this Brew (see docs/design/
 * coffee-counter-chat-ui-design.md non-goals).
 */

export interface BaseEvent {
  request_id: string;
  ts: string; // ISO-8601 UTC
}

export interface OrderReceivedEvent extends BaseEvent {
  event: "order_received";
  prompt_chars: number;
}

export interface ClassifyingEvent extends BaseEvent {
  event: "classifying";
}

export type Complexity = "espresso_shot" | "cold_brew";

export interface RouteSelectedEvent extends BaseEvent {
  event: "route_selected";
  bean_alias: string;
  task_type: string;
  complexity: Complexity;
  est_cost_usd: number | null;
  policy_entry: string;
  constraint_reason: string | null; // added in contract v1.2 (Brew 38)
}

export interface GeneratingEvent extends BaseEvent {
  event: "generating";
  tokens_out: number;
  est_cost_usd: number | null;
  text_delta: string | null; // added in contract v1.1
}

export type EscalationReason = "truncated" | "empty" | "refusal_shaped" | "caller_reported";

export interface EscalationPendingEvent extends BaseEvent {
  event: "escalation_pending";
  reason: EscalationReason;
  est_cost_usd: number;
  premium_bean_alias: string | null;
  // Added in contract v1.3 (Brew 40): the UTC instant this pause
  // auto-declines. null only when premium_bean_alias is null (nothing to
  // wait for). Lets the approval card show an accurate countdown and lets
  // the UI tell "declined" apart from "timed out" after the fact.
  decision_deadline: string | null;
}

export interface EscalatingEvent extends BaseEvent {
  event: "escalating";
  bean_alias: string;
}

export interface CompleteEvent extends BaseEvent {
  event: "complete";
  bean_alias: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number | null;
  latency_ms: number;
  escalated: boolean;
  draft_quality: boolean;
  // Added in contract v1.4 (Brew 41): the distinct source paths of the
  // Pantry chunks the router actually injected into this request's
  // context - not a model self-report. null when the request didn't set
  // use_pantry, or no chunks matched - never an empty-but-claimed array.
  pantry_sources: string[] | null;
  // Added in contract v1.5 (Brew 46): how much conversation history rode
  // along on this request. Both null when the session's remember_chat
  // was false - deliberately not 0, so the UI can tell "toggle is off"
  // apart from "toggle is on but this was turn one" (a real 0). See
  // docs/design/conversation-memory-design.md Section 4.
  history_turns: number | null;
  history_tokens_est: number | null;
  // Added in contract v1.6 (web search citations Brew): the distinct
  // source URLs OpenRouter's web search tool actually cited in this
  // response, deduplicated by URL. null when use_web was false or
  // nothing was cited - never an empty-but-claimed array, same
  // convention as pantry_sources. Never appears on GeneratingEvent - only
  // known once the full response is complete.
  web_sources: WebSource[] | null;
  // Added in contract v1.7 (Brew 57): what conversation history was
  // DROPPED to fit the window, so trimming is visible instead of silent.
  // Same null-vs-0 convention as v1.5's fields: all three null when
  // remember_chat was false, and history_turns_dropped is a real 0 - not
  // null - when the toggle is on and nothing was dropped, so the UI can
  // tell "nothing was dropped" apart from "not applicable".
  // history_drop_reason is null if and only if history_turns_dropped is 0.
  history_turns_dropped: number | null;
  history_chars_dropped: number | null;
  history_drop_reason: HistoryDropReason | null;
}

/**
 * Why history was trimmed (contract v1.7). Three distinct situations with
 * three different user remedies - see RememberChatToggle for the copy.
 */
export type HistoryDropReason =
  | "current_prompt_fills_window"
  | "single_turn_too_large"
  | "window_full";

// Added in contract v1.6 - see CompleteEvent.web_sources.
export interface WebSource {
  url: string;
  title: string;
}

export interface ErrorEvent extends BaseEvent {
  event: "error";
  error_type: string;
  message: string;
  retryable: boolean;
}

export interface CancelledEvent extends BaseEvent {
  event: "cancelled";
  reason: "client_disconnect" | "client_cancel_request";
}

/** Added in contract v1.3 (Brew 40): keep-alive only, sent when nothing
 * real has arrived for settings.sse_heartbeat_interval_seconds (mainly
 * during an escalation_pending pause). Carries no fields beyond the
 * shared base. Must be ignored for state purposes - see
 * reduceEventIntoMessage in chat.ts, which treats it as a no-op and
 * never lets it become a message's latestEvent. */
export interface HeartbeatEvent extends BaseEvent {
  event: "heartbeat";
}

export type RouterEvent =
  | OrderReceivedEvent
  | ClassifyingEvent
  | RouteSelectedEvent
  | GeneratingEvent
  | EscalationPendingEvent
  | EscalatingEvent
  | CompleteEvent
  | ErrorEvent
  | CancelledEvent
  | HeartbeatEvent;

export interface Bean {
  alias: string;
  role: string;
  available: boolean;
}

export interface SessionSummary {
  id: string;
  project: string;
  // Brew 43 (docs/design/auth-projects-chat-management-design.md
  // Section 4.1): the real projects table's id. null means "default"
  // (no project) - the legacy `project` string above is no longer a
  // real scoping mechanism on the client, kept only because the router
  // still returns it.
  project_id: number | null;
  title: string;
  created_at: string;
  updated_at: string;
  cost_total_usd: number;
  // Brew 46 (docs/design/conversation-memory-design.md Section 1):
  // per-session, user-controlled conversation memory. Defaults true for
  // every new session.
  remember_chat: boolean;
}

export interface StoredMessage {
  id: string;
  request_id: string;
  role: "user" | "assistant";
  content: string;
  bean_alias: string | null;
  task_type: string | null;
  complexity: Complexity | null;
  cost_usd: number | null;
  latency_ms: number | null;
  escalated: boolean | null;
  draft_quality: boolean | null;
  rating: Rating | null;
  created_at: string;
  // Brew 46: cheap boolean only - the router doesn't ship extracted
  // attachment text back over this endpoint, just whether this message
  // had one, so the "Turn on Remember chat to ask follow-ups about your
  // attachments" hint can detect the case without a heavier payload.
  has_attachments: boolean;
}

export type Rating = "good" | "needed_fixing" | "failed";

/** Shape of GET /v1/sessions/{id}/pending_escalation (Brew 40) - the same
 * information escalation_pending itself carries, for a client that
 * reloaded mid-pause and never saw that event live. See
 * docs/design/escalation-approval-ui-design.md Section 3.5. */
export interface PendingEscalationInfo {
  request_id: string;
  reason: EscalationReason;
  est_cost_usd: number;
  premium_bean_alias: string | null;
  started_at: string;
  decision_deadline: string;
}
