import type { RouterEvent } from "@/lib/events";

/**
 * Data-driven event-to-status-text mapping, matching the router's own
 * classifier table-not-ifs philosophy (router/app/classifier.py). This
 * table is the only thing that needs to change if wording changes -
 * nothing else in CounterDisplay should ever branch on event.event
 * directly. See docs/design/coffee-counter-chat-ui-design.md Section 5.2.
 */
export function statusTextFor(event: RouterEvent | null): string {
  if (event === null) return "Ready when you are";

  switch (event.event) {
    case "order_received":
      return "Taking your order";
    case "classifying":
      return "Thinking it over";
    case "route_selected":
      return `Reaching for the ${event.bean_alias} jar`;
    case "generating":
      return "Brewing";
    case "escalation_pending":
      return "Waiting for your approval";
    case "escalating":
      return `Reaching for the ${event.bean_alias} jar`;
    case "complete":
      return "Order up";
    case "error":
      return "Order dropped";
    case "cancelled":
      return "Order cancelled";
  }
}
