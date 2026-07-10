import type { RouterEvent } from "@/lib/events";

/**
 * The ONLY contract callers may depend on. Stage E (the animated scene)
 * replaces CounterDisplay's internals without any caller changing - see
 * docs/design/coffee-counter-chat-ui-design.md Section 5.2.
 */
export interface CounterDisplayProps {
  /** Latest SSE event for the active stream, or null when idle. */
  event: RouterEvent | null;
  /** "Tips Jar" running total for the active message. */
  sessionCostUsd: number;
}
