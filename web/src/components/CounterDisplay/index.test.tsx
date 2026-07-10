import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { CounterDisplay } from "@/components/CounterDisplay";
import { statusTextFor } from "@/components/CounterDisplay/statusText";
import type { RouterEvent } from "@/lib/events";

const REQUEST_ID = "req-1";
const TS = "2026-07-10T20:14:03.101Z";

describe("statusTextFor - event-to-text mapping table", () => {
  it("idle (null) shows the ready state", () => {
    expect(statusTextFor(null)).toBe("Ready when you are");
  });

  it("order_received", () => {
    const event: RouterEvent = { event: "order_received", request_id: REQUEST_ID, ts: TS, prompt_chars: 10 };
    expect(statusTextFor(event)).toBe("Taking your order");
  });

  it("classifying", () => {
    const event: RouterEvent = { event: "classifying", request_id: REQUEST_ID, ts: TS };
    expect(statusTextFor(event)).toBe("Thinking it over");
  });

  it("route_selected interpolates the bean alias", () => {
    const event: RouterEvent = {
      event: "route_selected",
      request_id: REQUEST_ID,
      ts: TS,
      bean_alias: "House Blend",
      task_type: "code",
      complexity: "espresso_shot",
      est_cost_usd: 0,
      policy_entry: "code/house-blend",
      constraint_reason: null,
    };
    expect(statusTextFor(event)).toBe("Reaching for the House Blend jar");
  });

  it("generating", () => {
    const event: RouterEvent = {
      event: "generating",
      request_id: REQUEST_ID,
      ts: TS,
      tokens_out: 10,
      est_cost_usd: 0,
      text_delta: "Hi",
    };
    expect(statusTextFor(event)).toBe("Brewing");
  });

  it("escalation_pending", () => {
    const event: RouterEvent = {
      event: "escalation_pending",
      request_id: REQUEST_ID,
      ts: TS,
      reason: "truncated",
      est_cost_usd: 0.5,
      premium_bean_alias: "Reserve Blend",
    };
    expect(statusTextFor(event)).toBe("Waiting for your approval");
  });

  it("escalating interpolates the premium bean alias", () => {
    const event: RouterEvent = {
      event: "escalating",
      request_id: REQUEST_ID,
      ts: TS,
      bean_alias: "Reserve Blend",
    };
    expect(statusTextFor(event)).toBe("Reaching for the Reserve Blend jar");
  });

  it("complete", () => {
    const event: RouterEvent = {
      event: "complete",
      request_id: REQUEST_ID,
      ts: TS,
      bean_alias: "House Blend",
      tokens_in: 1,
      tokens_out: 2,
      cost_usd: 0,
      latency_ms: 100,
      escalated: false,
      draft_quality: false,
    };
    expect(statusTextFor(event)).toBe("Order up");
  });

  it("error", () => {
    const event: RouterEvent = {
      event: "error",
      request_id: REQUEST_ID,
      ts: TS,
      error_type: "provider_error",
      message: "boom",
      retryable: true,
    };
    expect(statusTextFor(event)).toBe("Order dropped");
  });

  it("cancelled", () => {
    const event: RouterEvent = {
      event: "cancelled",
      request_id: REQUEST_ID,
      ts: TS,
      reason: "client_cancel_request",
    };
    expect(statusTextFor(event)).toBe("Order cancelled");
  });
});

describe("CounterDisplay component", () => {
  it("renders the mapped status text for the given event", () => {
    render(<CounterDisplay event={null} sessionCostUsd={0} />);
    expect(screen.getByTestId("counter-display-status")).toHaveTextContent("Ready when you are");
  });

  it("renders the Tips Jar total, tabular-nums formatted to 4 decimal places", () => {
    render(<CounterDisplay event={null} sessionCostUsd={0.1234} />);
    expect(screen.getByTestId("counter-display-tips-jar")).toHaveTextContent("$0.1234");
  });

  it("updates status text when a generating event arrives", () => {
    const event: RouterEvent = {
      event: "generating",
      request_id: REQUEST_ID,
      ts: TS,
      tokens_out: 10,
      est_cost_usd: 0,
      text_delta: "Hi",
    };
    render(<CounterDisplay event={event} sessionCostUsd={0} />);
    expect(screen.getByTestId("counter-display-status")).toHaveTextContent("Brewing");
  });
});
