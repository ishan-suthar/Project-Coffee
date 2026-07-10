/**
 * SSE event types mirroring router/EVENT_CONTRACT.md (v1.2) and
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

export type RouterEvent =
  | OrderReceivedEvent
  | ClassifyingEvent
  | RouteSelectedEvent
  | GeneratingEvent
  | EscalationPendingEvent
  | EscalatingEvent
  | CompleteEvent
  | ErrorEvent
  | CancelledEvent;

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
