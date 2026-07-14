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
  title: string;
  created_at: string;
  updated_at: string;
  cost_total_usd: number;
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
