import { describe, expect, it } from "vitest";
import {
  JAR_KEYS,
  jarBooleansFor,
  jarKeyFor,
  machineFor,
  sceneStateIndexFor,
} from "@/components/CounterDisplay/sceneState";
import type { RouterEvent } from "@/lib/events";

const REQUEST_ID = "req-1";
const TS = "2026-07-11T20:14:03.101Z";

function eventOf(event: RouterEvent["event"]): RouterEvent {
  switch (event) {
    case "order_received":
      return { event, request_id: REQUEST_ID, ts: TS, prompt_chars: 10 };
    case "classifying":
      return { event, request_id: REQUEST_ID, ts: TS };
    case "route_selected":
      return {
        event,
        request_id: REQUEST_ID,
        ts: TS,
        bean_alias: "House Blend",
        task_type: "code",
        complexity: "espresso_shot",
        est_cost_usd: 0,
        policy_entry: "code/house-blend",
        constraint_reason: null,
      };
    case "generating":
      return { event, request_id: REQUEST_ID, ts: TS, tokens_out: 1, est_cost_usd: 0, text_delta: "hi" };
    case "escalation_pending":
      return {
        event,
        request_id: REQUEST_ID,
        ts: TS,
        reason: "truncated",
        est_cost_usd: 0.5,
        premium_bean_alias: "Reserve Blend",
        decision_deadline: "2026-07-11T20:24:03.101Z",
      };
    case "escalating":
      return { event, request_id: REQUEST_ID, ts: TS, bean_alias: "Reserve Blend" };
    case "complete":
      return {
        event,
        request_id: REQUEST_ID,
        ts: TS,
        bean_alias: "House Blend",
        tokens_in: 10,
        tokens_out: 10,
        cost_usd: 0,
        latency_ms: 100,
        escalated: false,
        draft_quality: false,
        pantry_sources: null,
        history_turns: null,
        history_tokens_est: null,
        history_turns_dropped: null,
        history_chars_dropped: null,
        history_drop_reason: null,
        web_sources: null,
      };
    case "error":
      return { event, request_id: REQUEST_ID, ts: TS, error_type: "provider_error", message: "x", retryable: true };
    case "cancelled":
      return { event, request_id: REQUEST_ID, ts: TS, reason: "client_cancel_request" };
    case "heartbeat":
      return { event, request_id: REQUEST_ID, ts: TS };
  }
}

describe("sceneStateIndexFor", () => {
  it("maps idle (null) to 0", () => {
    expect(sceneStateIndexFor(null)).toBe(0);
  });

  const table: [RouterEvent["event"], number][] = [
    ["order_received", 1],
    ["classifying", 2],
    ["route_selected", 3],
    ["generating", 4],
    ["escalation_pending", 5],
    ["escalating", 6],
    ["complete", 7],
    ["error", 8],
    ["cancelled", 8],
    ["heartbeat", 4], // unreachable in practice - see sceneState.ts's comment
  ];

  for (const [eventName, expected] of table) {
    it(`maps ${eventName} to state ${expected}`, () => {
      expect(sceneStateIndexFor(eventOf(eventName))).toBe(expected);
    });
  }

  it("cancelled and error share state 8 but are distinguishable via statusText.ts, not a 9th state", () => {
    expect(sceneStateIndexFor(eventOf("cancelled"))).toBe(sceneStateIndexFor(eventOf("error")));
  });
});

describe("jarKeyFor", () => {
  it("maps every real Bean alias to its own jar key", () => {
    expect(jarKeyFor("House Blend")).toBe("jar_house_blend");
    expect(jarKeyFor("Second Pour")).toBe("jar_second_pour");
    expect(jarKeyFor("Guest Bean")).toBe("jar_guest_bean");
    expect(jarKeyFor("Reserve Blend")).toBe("jar_reserve_blend");
  });

  it("falls back to jar_default for an unrecognized alias, never guessing a real one", () => {
    expect(jarKeyFor("Some Future Bean")).toBe("jar_default");
  });

  it("returns null when there is no alias yet", () => {
    expect(jarKeyFor(null)).toBeNull();
  });
});

describe("jarBooleansFor", () => {
  it("has exactly one true jar during route_selected (state 3)", () => {
    const result = jarBooleansFor(3, "Second Pour");
    const trueKeys = JAR_KEYS.filter((key) => result[key]);
    expect(trueKeys).toEqual(["jar_second_pour"]);
  });

  it("has exactly one true jar during generating (state 4)", () => {
    const result = jarBooleansFor(4, "Reserve Blend");
    const trueKeys = JAR_KEYS.filter((key) => result[key]);
    expect(trueKeys).toEqual(["jar_reserve_blend"]);
  });

  it("has no true jar outside states 3-4", () => {
    for (const state of [0, 1, 2, 5, 6, 7, 8] as const) {
      const result = jarBooleansFor(state, "House Blend");
      expect(JAR_KEYS.some((key) => result[key])).toBe(false);
    }
  });

  it("has no true jar when beanAlias is null even during states 3-4", () => {
    expect(JAR_KEYS.some((key) => jarBooleansFor(3, null)[key])).toBe(false);
    expect(JAR_KEYS.some((key) => jarBooleansFor(4, null)[key])).toBe(false);
  });
});

describe("machineFor", () => {
  it("shows the espresso machine for espresso_shot complexity during generating", () => {
    expect(machineFor(4, "espresso_shot")).toBe("espresso");
  });

  it("shows the pour-over machine for cold_brew complexity during generating", () => {
    expect(machineFor(4, "cold_brew")).toBe("pour_over");
  });

  it("shows no machine outside the generating state", () => {
    expect(machineFor(3, "espresso_shot")).toBeNull();
    expect(machineFor(7, "cold_brew")).toBeNull();
  });

  it("shows no machine when complexity is unexpectedly null during generating, rather than guessing", () => {
    expect(machineFor(4, null)).toBeNull();
  });
});
