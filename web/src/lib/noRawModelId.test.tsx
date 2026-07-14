import { describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import { CounterDisplay } from "@/components/CounterDisplay";
import { MessageHeader } from "@/components/ResponseSection/MessageHeader";
import { newAssistantMessage } from "@/lib/chat";
import * as preferences from "@/lib/preferences";
import type { RouterEvent } from "@/lib/events";

vi.mock("@/lib/preferences");
vi.mocked(preferences.getPreferences).mockResolvedValue({});
vi.mocked(preferences.setPreference).mockResolvedValue(undefined);

// BaristaScene needs a real WASM/canvas context jsdom can't provide - see
// CounterDisplay/SceneShell.test.tsx for the same stub approach.
vi.mock("@/components/CounterDisplay/BaristaScene", () => ({
  BaristaScene: () => <div data-testid="mock-barista-scene" />,
}));

/**
 * Requirement 8 (docs/design/coffee-counter-chat-ui-design.md): raw model
 * IDs must never appear anywhere in the UI. This fixture list mirrors the
 * real router/config/beans.yaml model_id values at the time this test was
 * written - the Playwright smoke test (e2e/chat.spec.ts) does the
 * stronger version of this check by pulling the live list from the
 * running router's /v1/beans endpoint against real rendered output.
 */
const RAW_MODEL_IDS = [
  "nvidia/nemotron-3-ultra-550b-a55b:free",
  "cohere/north-mini-code:free",
  "poolside/laguna-m.1:free",
];

const REQUEST_ID = "req-1";
const TS = "2026-07-10T20:14:03.101Z";

describe("Requirement 8: raw model IDs never appear in the UI", () => {
  it("CounterDisplay never renders a raw model ID for any event type", () => {
    const events: (RouterEvent | null)[] = [
      null,
      { event: "order_received", request_id: REQUEST_ID, ts: TS, prompt_chars: 10 },
      { event: "classifying", request_id: REQUEST_ID, ts: TS },
      {
        event: "route_selected",
        request_id: REQUEST_ID,
        ts: TS,
        bean_alias: "House Blend",
        task_type: "code",
        complexity: "espresso_shot",
        est_cost_usd: 0,
        policy_entry: "code/house-blend",
        constraint_reason: null,
      },
      {
        event: "generating",
        request_id: REQUEST_ID,
        ts: TS,
        tokens_out: 10,
        est_cost_usd: 0,
        text_delta: "Hi",
      },
      {
        event: "escalating",
        request_id: REQUEST_ID,
        ts: TS,
        bean_alias: "Reserve Blend",
      },
    ];

    for (const event of events) {
      const { container, unmount } = render(
        <CounterDisplay
          event={event}
          sessionCostUsd={0}
          beanAlias={null}
          complexity={null}
          hasVisibleContent={false}
        />
      );
      for (const rawId of RAW_MODEL_IDS) {
        expect(container.textContent).not.toContain(rawId);
      }
      unmount();
    }
  });

  it("MessageHeader never renders a raw model ID even with escalation detail expanded", () => {
    const message = {
      ...newAssistantMessage(REQUEST_ID),
      isStreaming: false,
      beanAlias: "House Blend",
      costUsd: 0.01,
      latencyMs: 500,
      escalation: {
        reason: "truncated" as const,
        estCostUsd: 0.5,
        premiumBeanAlias: "Reserve Blend",
        decisionDeadline: null,
      },
    };

    const { container } = render(<MessageHeader message={message} />);
    for (const rawId of RAW_MODEL_IDS) {
      expect(container.textContent).not.toContain(rawId);
    }
  });
});
