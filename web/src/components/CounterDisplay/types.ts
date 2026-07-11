import type { Complexity, RouterEvent } from "@/lib/events";

/**
 * The ONLY contract callers may depend on. Stage E (the animated scene)
 * replaces CounterDisplay's internals without any caller changing - see
 * docs/design/coffee-counter-chat-ui-design.md Section 5.2.
 *
 * beanAlias, complexity, and hasVisibleContent were added in Brew 39
 * (docs/design/counter-scene-design.md Section 3.2/3.4) - all three are
 * additive, all three are sourced from data page.tsx already tracks on
 * the active message (the same pattern sessionCostUsd already used), and
 * all three exist because a `generating` event carries neither a bean
 * alias nor a complexity - without them the scene would have to guess
 * mid-stream, which the brief for the animated scene explicitly forbids.
 */
export interface CounterDisplayProps {
  /** Latest SSE event for the active stream, or null when idle. */
  event: RouterEvent | null;
  /** "Tips Jar" running total for the active message. */
  sessionCostUsd: number;
  /** Carried forward from the most recent route_selected/escalating event
   * for the active message - generating carries neither field itself. */
  beanAlias: string | null;
  complexity: Complexity | null;
  /** True once any streamed text has rendered for the active message -
   * used only to bound the complete-state fade-zone sync buffer to at
   * most 300ms (Requirement 4), never to infer pipeline state. */
  hasVisibleContent: boolean;
}
